from camel.loaders.mineru_extractor import MinerU
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits import ImageAnalysisToolkit, AudioAnalysisToolkit, VideoAnalysisToolkit, ExcelToolkit
from camel.messages import BaseMessage
from camel.models import ModelFactory, BaseModelBackend
from camel.types import ModelType, ModelPlatformType
from camel.models import OpenAIModel, DeepSeekModel
from camel.agents import ChatAgent
from docx2markdown._docx_to_markdown import docx_to_markdown
import openai
import requests
import mimetypes
import json
from retry import retry
from typing import List, Dict, Any, Optional, Tuple, Literal
from PIL import Image
from io import BytesIO
from loguru import logger
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urlparse, urljoin
import os
import subprocess
import xmltodict
import asyncio
import nest_asyncio
nest_asyncio.apply()


class DocumentProcessingToolkit(BaseToolkit):
    r"""A class representing a toolkit for processing document and return the content of the document.

    This class provides method for processing docx, pdf, pptx, etc. It cannot process excel files.
    """
    def __init__(self, cache_dir: Optional[str] = None):
        self.image_tool = ImageAnalysisToolkit()
        self.audio_tool = AudioAnalysisToolkit()
        self.excel_tool = ExcelToolkit()
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }

        self.cache_dir = cache_dir or "tmp/"
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
    
    @retry((requests.RequestException))
    def extract_document_content(self, document_path: str, query: str = None) -> Tuple[bool, str]:
        r"""Extract the content of a given document (or url) and return the processed text.
        It may filter out some information, resulting in inaccurate content.

        Args:
            document_path (str): The path of the document to be processed, either a local path or a URL. It can process image, audio files, zip files and webpages, etc.
            query (str): The query to be used for retrieving the content. If the content is too long, the query will be used to identify which part contains the relevant information (like RAG). The query should be consistent with the current task.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the document was processed successfully, and the content of the document (if success).
        """
        logger.debug(f"Calling extract_document_content function with document_path=`{document_path}`")

        if any(document_path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            res = self.image_tool.ask_question_about_image(document_path, "Please make a detailed caption about the image.")
            return True, res
        
        if any(document_path.endswith(ext) for ext in ['.mp3', '.wav']):
            res = self.audio_tool.ask_question_about_audio(document_path, "Please transcribe the audio content to text.")
            return True, res
        
        if any(document_path.endswith(ext) for ext in ['txt']):
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            f.close()
            res = self._post_process_result(content, query)
            return True, res
        
        if any(document_path.endswith(ext) for ext in ['xls', 'xlsx']):
            res = self.excel_tool.extract_excel_content(document_path)
            return True, res

        if any(document_path.endswith(ext) for ext in ['zip']): 
            extracted_files = self._unzip_file(document_path)
            return True, f"The extracted files are: {extracted_files}"

        if any(document_path.endswith(ext) for ext in ['json', 'jsonl', 'jsonld']):
            with open(document_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            f.close()
            return True, content
        
        if any(document_path.endswith(ext) for ext in ['py']):
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            f.close()
            return True, content

        
        if any(document_path.endswith(ext) for ext in ['xml']):
            data = None
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            f.close()

            try:
                data = xmltodict.parse(content)
                logger.debug(f"The extracted xml data is: {data}")
                return True, data
            
            except Exception as e:
                logger.debug(f"The raw xml data is: {content}")
                return True, content


        if self._is_webpage(document_path):
            
            extracted_text = self._extract_webpage_content(document_path)      
            result_filtered = self._post_process_result(extracted_text, query)
            return True, result_filtered
        

        else:
            # judge if url
            parsed_url = urlparse(document_path)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            if not is_url:
                if not os.path.exists(document_path):
                    return f"Document not found at path: {document_path}."

            # if is docx file, use docx2markdown to convert it
            if document_path.endswith(".docx"):
                if is_url:
                    tmp_path = self._download_file(document_path)
                else:
                    tmp_path = document_path
                
                file_name = os.path.basename(tmp_path)
                md_file_path = os.path.join(self.cache_dir, f"{file_name}.md")
                docx_to_markdown(tmp_path, md_file_path)

                # load content of md file
                with open(md_file_path, "r", encoding="utf-8") as f:
                    extracted_text = f.read()
                f.close()
                return True, extracted_text
            
            if document_path.endswith(".pptx"):
                # use unstructured to extract text from pptx
                try:
                    from unstructured.partition.auto import partition
                    extracted_text = partition(document_path)
                    #return a list of text
                    extracted_text = [item.text for item in extracted_text]
                    return True, extracted_text
                except Exception as e:
                    logger.error(f"Error occurred while processing pptx: {e}")
                    return False, f"Error occurred while processing pptx: {e}"
            
            try:
                result = self._extract_content_with_mineru(document_path)
                logger.debug(f"The extracted text from MinerU is: {result}")
                result_filtered = self._post_process_result(result, query)
                return True, result_filtered

            except Exception as e:
                logger.warning(f"Error occurred while using MinerU to process document: {e}")
                if document_path.endswith(".pdf"):
                    # try using pypdf to extract text from pdf
                    try:
                        from PyPDF2 import PdfReader
                        if is_url:
                            tmp_path = self._download_file(document_path)
                            document_path = tmp_path

                        with open(document_path, 'rb') as f:
                            reader = PdfReader(f)
                            extracted_text = ""
                            for page in reader.pages:
                                extracted_text += page.extract_text()
                        
                        result_filtered = self._post_process_result(extracted_text, query)
                        return True, result_filtered

                    except Exception as e:
                        logger.error(f"Error occurred while processing pdf: {e}")
                        return False, f"Error occurred while processing pdf: {e}"
                
                # use unstructured to extract text from file
                try:
                    from unstructured.partition.auto import partition
                    extracted_text = partition(document_path)
                    #return a list of text
                    extracted_text = [item.text for item in extracted_text]
                    return True, extracted_text
                
                except Exception as e:
                    logger.error(f"Error occurred while processing document: {e}")
                    return False, f"Error occurred while processing document: {e}"
    
    
    def _post_process_result(self, result: str, query: str, process_model: BaseModelBackend = None) -> str:
        r"""Identify whether the result is too long. If so, split it into multiple parts, and leverage a model to identify which part contains the relevant information.
        """
        import concurrent.futures
        
        def _identify_relevant_part(part_idx: int, part: str, query: str, _process_model: BaseModelBackend = None) -> Tuple[bool, str]:
            agent = ChatAgent(
                model=_process_model
            )
            
            prompt = f"""
I have retrieved some information from a long document. 
Now I have split the document into multiple parts. Your task is to identify whether the given part contains the relevant information based on the query.

If it does, return only "True". If it doesn't, return only "False". Do not return any other information.

Document part:
<document_part>
{part}
</document_part>

Query:
<query>
{query}
</query>
"""
            
            response = agent.step(prompt)
            if "true" in response.msgs[0].content.lower():
                return True, part_idx, part
            else:
                return False, part_idx, part
        
        
        if process_model is None:
            process_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.O3_MINI,
                model_config_dict={"temperature": 0.0}
            )
            
        max_length = 200000
        split_length = 40000
        
        if len(result) > max_length:
            # split the result into multiple parts
            logger.debug(f"The original result is too long. Splitting it into multiple parts. query: {query}")
            parts = [result[i:i+split_length] for i in range(0, len(result), split_length)]
            result_cache = {}
            # use concurrent.futures to process the parts
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(_identify_relevant_part, part_idx, part, query, process_model) for part_idx, part in enumerate(parts)]
                for future in concurrent.futures.as_completed(futures):
                    is_relevant, part_idx, part = future.result()
                    if is_relevant:
                        result_cache[part_idx] = part
            # re-assemble the parts according to the part_idx
            result_filtered = ""
            for part_idx in sorted(result_cache.keys()):
                result_filtered += result_cache[part_idx]
                result_filtered += "..."
            
            result_filtered += "(The above is the re-assembled result of the document, because the original document is too long. If empty, it means no relevant information found.)"
            if len(result_filtered) > max_length:
                result_filtered = result_filtered[:max_length]          # TODO: Refine it to be more accurate
            logger.debug(f"split context length: {len(result_filtered)}")
            return result_filtered
        
        else:
            return result


    def _is_webpage(self, url: str) -> bool:
        r"""Judge whether the given URL is a webpage."""
        try:
            parsed_url = urlparse(url)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            if not is_url:
                return False

            path = parsed_url.path
            file_type, _ = mimetypes.guess_type(path)
            if 'text/html' in file_type:
                return True
            
            response = requests.head(url, allow_redirects=True, timeout=10)
            content_type = response.headers.get("Content-Type", "").lower()
            
            if "text/html" in content_type:
                return True
            else:
                return False
        
        except requests.exceptions.RequestException as e:
            # raise RuntimeError(f"Error while checking the URL: {e}")
            logger.warning(f"Error while checking the URL: {e}")
            return False

        except TypeError:
            return True
    

    @retry(requests.RequestException)
    def _extract_content_with_mineru(self, document_path: str) -> str:
        """Extract content from document using MinerU API.

        Args:
            document_path: Path to the document (URL or local file path)

        Returns:
            Extracted text content from the document
        """
        api_key = os.getenv("MINERU_API_KEY")
        if not api_key:
            raise ValueError("MINERU_API_KEY environment variable is not set")

        mineru = MinerU(
            api_key=api_key,
            is_ocr=True,
            enable_formula=True,
            enable_table=True,
        )

        # Check if it's a URL or local file
        parsed_url = urlparse(document_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        if not is_url:
            # For local files, we need to upload first
            # MinerU API may not support direct file upload, so we raise an error
            # and let the fallback methods handle it
            raise ValueError("MinerU API requires a URL. Local file processing will use fallback methods.")

        # For URLs, use extract_url directly
        logger.debug(f"Extracting content from URL using MinerU: {document_path}")
        response = mineru.extract_url(document_path)
        task_id = response.get('task_id')

        if not task_id:
            raise RuntimeError(f"MinerU API did not return a task_id. Response: {response}")

        logger.debug(f"MinerU task created: {task_id}")

        # Wait for the task to complete
        result = mineru.wait_for_completion(task_id, timeout=300)
        logger.debug(f"MinerU task completed. State: {result.get('state')}")

        # Extract the markdown content from the result
        if result.get('state') == 'done':
            # Get the full_md_content or md_content
            md_content = result.get('full_md_content') or result.get('md_content', '')
            if md_content:
                return md_content

            # If no markdown content, try to get from download URL
            md_url = result.get('full_md_url') or result.get('md_url')
            if md_url:
                logger.debug(f"Downloading markdown from URL: {md_url}")
                md_response = requests.get(md_url)
                md_response.raise_for_status()
                return md_response.text

            logger.warning(f"Document processed but no content extracted. Result keys: {result.keys()}")
            return f"Document processed but no content extracted. Result: {result}"
        else:
            raise RuntimeError(f"MinerU task failed: {result.get('err_msg', 'Unknown error')}")
    
    
    @retry(requests.RequestException, delay=60, backoff=2, max_delay=120)
    def _extract_webpage_content_with_html2text(self, url: str, timeout: int = 600) -> str:
        """Extract webpage content using html2text with timeout.

        Args:
            url: The URL to extract content from.
            timeout: Timeout in seconds (default 600 = 10 minutes).

        Returns:
            Extracted text content, or empty string if timeout/error occurs.
        """
        import html2text
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        logger.debug(f"Trying to use html2text to get the text. html2text can sometimes hang, using {timeout}s timeout.")

        response = requests.get(url, headers=self.headers, timeout=60)
        html_content = response.text

        def process_html():
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_tables = False
            return h.handle(html_content)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(process_html)
                extracted_text = future.result(timeout=timeout)
                return extracted_text
        except FuturesTimeoutError:
            logger.warning(f"html2text timed out after {timeout}s for URL: {url}")
            return ""
        except Exception as e:
            logger.warning(f"html2text failed with error: {e}")
            return ""
    
    @retry(requests.RequestException, delay=60, backoff=2, max_delay=120)
    def _extract_webpage_content_with_beautifulsoup(self, url: str) -> str:
        response = requests.get(url, headers=self.headers)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted_text = soup.get_text()
        return extracted_text
    

    @retry(RuntimeError, delay=60, backoff=2, max_delay=120)
    def _extract_webpage_content(self, url: str) -> str:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        from firecrawl import FirecrawlApp

        # Initialize the FirecrawlApp with your API key
        app = FirecrawlApp(api_key=api_key)

        try:
            data = app.scrape(url, formats=['markdown'])

        except Exception as e:
            if '403' in str(e):
                logger.error(f"Error: {e}")
                return str(e)
            elif "429" in str(e):
                # too many requests
                logger.error(f"Error: {e}")
                raise RuntimeError(f"Error: {e}")

            elif "Payment Required" in str(e):
                logger.error(f"Error: {e}")
                extracted_text = self._extract_webpage_content_with_html2text(url)
                logger.debug(f"The extracted text from html2text is: {extracted_text}")
                return extracted_text
            else:
                raise e

        logger.debug(f"Extracted data from {url} using firecrawl: {data}")

        # Handle response - firecrawl v1.0+ returns object with .markdown property
        markdown_content = getattr(data, 'markdown', None) or data.get('markdown') if isinstance(data, dict) else None
        if not markdown_content:
            logger.debug(f"Trying to use html2text to get the text.")
            extracted_text = self._extract_webpage_content_with_html2text(url)
            logger.debug(f"The extracted text from html2text is: {extracted_text}")

            if len(extracted_text) == 0:
                return "No content found on the webpage."
            else:
                return extracted_text

        return str(markdown_content)
    

    def _download_file(self, url: str):
        r"""Download a file from a URL and save it to the cache directory."""
        try:
            response = requests.get(url, stream=True, headers=self.headers)
            response.raise_for_status() 
            file_name = url.split("/")[-1]  

            file_path = os.path.join(self.cache_dir, file_name)

            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            return file_path

        except requests.exceptions.RequestException as e:
            print(f"Error downloading the file: {e}")


    def _get_formatted_time(self) -> str:
        import time
        return time.strftime("%m%d%H%M")

    
    def _unzip_file(self, zip_path: str) -> List[str]:
        if not zip_path.endswith('.zip'):
            raise ValueError("Only .zip files are supported")
        
        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        extract_path = os.path.join(self.cache_dir, zip_name)
        os.makedirs(extract_path, exist_ok=True)

        try:
            subprocess.run(["unzip", "-o", zip_path, "-d", extract_path], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to unzip file: {e}")

        extracted_files = []
        for root, _, files in os.walk(extract_path):
            for file in files:
                extracted_files.append(os.path.join(root, file))
        
        return extracted_files


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.extract_document_content),
        ]
