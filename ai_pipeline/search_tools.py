import logging
import os
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class WebSearchTool:
    def __init__(self, project_id: str, location: str, credentials=None):
        logger.info("Initializing WebSearchTool")
        
        # If credentials are provided, ensure they have the right scopes
        if credentials and hasattr(credentials, 'with_scopes'):
            # Add the required scopes for Vertex AI
            credentials = credentials.with_scopes([
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/generative-language'
            ])
            # Refresh the credentials
            if hasattr(credentials, 'refresh'):
                credentials.refresh(Request())
        
        # Set environment variables for the new SDK
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
        
        try:
            from google import genai
            from google.genai.types import (
                GenerateContentConfig,
                GoogleSearch,
                HttpOptions,
                Tool,
            )
            
            # Initialize the new genai client with credentials if provided
            if credentials:
                self.client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location=location,
                    credentials=credentials,
                    http_options=HttpOptions(api_version="v1")
                )
            else:
                # Try with default credentials
                self.client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location=location,
                    http_options=HttpOptions(api_version="v1")
                )
            
            self.genai = genai
            self.GenerateContentConfig = GenerateContentConfig
            self.GoogleSearch = GoogleSearch
            self.Tool = Tool
            
            logger.info("WebSearchTool initialized successfully with google-genai SDK")
            self.use_new_sdk = True
        except Exception as e:
            logger.warning(f"google-genai SDK initialization failed: {e}, falling back to vertexai SDK")
            # Fallback to vertexai SDK
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            vertexai.init(project=project_id, location=location, credentials=credentials)
            self.model = GenerativeModel(model_name="gemini-1.5-flash")
            self.use_new_sdk = False

    def search(self, query: str) -> str:
        """Performs a web search for the given query using Gemini with Google Search tool."""
        """
        args:
            query: str
        returns:
            str: The search results
        """
        logger.info(f"Performing web search for: '{query}'")
        
        if self.use_new_sdk:
            try:
                # Use the new SDK approach
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents=query,
                    config=self.GenerateContentConfig(
                        tools=[
                            self.Tool(google_search=self.GoogleSearch())
                        ],
                    ),
                )
                logger.info("Web search successful.")
                return response.text
            except Exception as e:
                logger.error(f"Web search failed with new SDK: {e}", exc_info=True)
                # Try without search grounding
                try:
                    logger.info("Retrying without search grounding...")
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash-001",
                        contents=query
                    )
                    return response.text
                except Exception as e2:
                    logger.error(f"Fallback generation also failed: {e2}")
                    return f"Sorry, I couldn't perform the search. Error: {e}"
        else:
            try:
                # Fallback to basic generation without explicit search tools
                response = self.model.generate_content(query)
                logger.info("Generated response without explicit search grounding.")
                return response.text
            except Exception as e:
                logger.error(f"Generation failed: {e}", exc_info=True)
                return f"Sorry, I couldn't process your query. Error: {e}"