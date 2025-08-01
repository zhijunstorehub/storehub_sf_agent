import logging
import json
import time
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Provides services to analyze Salesforce metadata using an LLM.
    """

    def __init__(self, api_key: str = None):
        """
        Initializes the AnalysisService.

        Args:
            api_key (str, optional): The API key for the LLM provider. Defaults to None.
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.use_real_api = bool(self.api_key and self.api_key != 'your_gemini_api_key' and len(self.api_key) > 10)
        
        if self.use_real_api:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("AnalysisService initialized with real Gemini API.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API: {e}. Falling back to mock responses.")
                self.use_real_api = False
        else:
            logger.info(f"AnalysisService initialized with mock responses (API key: {'Found' if self.api_key else 'Not found'}).")

    def _call_llm_api(self, prompt: str) -> dict:
        """
        Makes a call to the LLM API or returns mock response.
        """
        if self.use_real_api:
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Try to extract JSON from the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    return json.loads(json_str)
                else:
                    # If no JSON found, create a response
                    return {
                        "description": response_text,
                        "confidence_score": 7.5
                    }
                    
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                return {
                    "description": f"Error analyzing field: {str(e)}",
                    "confidence_score": 1.0
                }
        else:
            # Mock response for testing
            logger.info("Using mock LLM response...")
            time.sleep(0.1)  # Simulate faster mock response
            
            return {
                "description": "This is a mock AI-generated description. To get real analysis, please set your GEMINI_API_KEY environment variable.",
                "confidence_score": 5.0
            }

    def _construct_prompt(self, field_metadata: dict, object_name: str) -> str:
        """Constructs a detailed prompt for the LLM."""
        
        # Clean up metadata for a cleaner prompt
        prompt_data = {
            "objectApiName": object_name,
            "fieldApiName": field_metadata.get('name'),
            "label": field_metadata.get('label'),
            "dataType": field_metadata.get('type'),
            "length": field_metadata.get('length'),
            "isCustom": field_metadata.get('custom'),
            "existingHelpText": field_metadata.get('inlineHelpText'),
        }

        prompt = f"""
        You are a Salesforce expert analyzing field metadata. Analyze the following field and provide a business-oriented description.

        Field Information:
        {json.dumps(prompt_data, indent=2)}

        Instructions:
        1. If this is a custom field (API name ends with __c), analyze its likely business purpose based on the field name, label, and type
        2. If existing help text is provided and clear, you may refine it, but keep the core meaning
        3. Focus on WHY this field exists from a business perspective
        4. Provide a confidence score from 1-10 based on how clear the field's purpose is from the metadata

        Respond with ONLY a JSON object containing:
        {{
            "description": "Clear, business-focused description of what this field is used for",
            "confidence_score": 8.5
        }}
        """
        return prompt

    def analyze_field(self, field_metadata: dict, object_name: str) -> dict:
        """
        Analyzes a single field's metadata.

        If the field is standard and has a description, it's used directly with high confidence.
        If the field is custom, it calls the LLM for analysis.

        Args:
            field_metadata (dict): The metadata for a single field.
            object_name (str): The API name of the parent object.

        Returns:
            dict: A dictionary containing the analysis results, including
                  'description', 'source', and 'confidence_score'.
        """
        is_custom = field_metadata.get('custom', False)
        description = field_metadata.get('inlineHelpText')
        field_name = field_metadata.get('name', '')

        # Rule 1: Standard field with existing description - HIGH confidence
        if not is_custom and description:
            logger.debug(f"Using existing Salesforce description for standard field {object_name}.{field_name}")
            return {
                "description": description,
                "source": "Salesforce",
                "confidence_score": 10.0,  # Max confidence for official docs
                "needs_review": False
            }

        # Rule 2: Standard field without description - MEDIUM confidence with generic description
        if not is_custom and not description:
            logger.debug(f"Standard field {object_name}.{field_name} has no description")
            return {
                "description": f"Standard Salesforce field. {field_metadata.get('label', field_name)} is a built-in field for {object_name} objects.",
                "source": "Salesforce",
                "confidence_score": 8.0,  # High confidence for standard fields
                "needs_review": False
            }

        # Rule 3: Custom field - analyze with LLM
        logger.info(f"Analyzing custom field {object_name}.{field_name} with LLM.")
        prompt = self._construct_prompt(field_metadata, object_name)
        
        try:
            llm_result = self._call_llm_api(prompt)
            confidence = llm_result.get('confidence_score', 5.0)
            
            return {
                "description": llm_result.get('description', 'Analysis failed - no description returned.'),
                "source": "Gemini" if self.use_real_api else "Mock",
                "confidence_score": confidence,
                "needs_review": confidence < 7.0  # Flag for review if confidence is below 7
            }
        except Exception as e:
            logger.error(f"Failed to analyze field with LLM: {e}")
            return {
                "description": "Analysis failed due to an error.",
                "source": "Error",
                "confidence_score": 0.0,
                "needs_review": True
            }

# Example of how to use the service
if __name__ == '__main__':
    logger.info("Running AnalysisService demonstration...")
    
    # Test with environment variable
    analysis_service = AnalysisService()

    # Mock metadata for a custom field
    mock_custom_field = {
        "custom": True,
        "name": "Opportunity_Score__c",
        "label": "Opportunity Score",
        "type": "Number",
        "inlineHelpText": "Calculated score indicating sales potential."
    }
    
    # Mock metadata for a standard field
    mock_standard_field = {
        "custom": False,
        "name": "AnnualRevenue",
        "label": "Annual Revenue",
        "type": "Currency",
        "inlineHelpText": "The estimated annual revenue of the account."
    }
    
    print("\n--- Analyzing Custom Field ---")
    analysis1 = analysis_service.analyze_field(mock_custom_field, "Opportunity")
    print(json.dumps(analysis1, indent=2))
    
    print("\n--- Analyzing Standard Field ---")
    analysis2 = analysis_service.analyze_field(mock_standard_field, "Account")
    print(json.dumps(analysis2, indent=2))
