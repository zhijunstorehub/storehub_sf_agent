import logging
import json
import time
import os
import re
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelCapability(Enum):
    SIMPLE = "simple"      # Standard fields, basic descriptions
    MEDIUM = "medium"      # Common custom fields  
    COMPLEX = "complex"    # Ambiguous fields, need context inference

@dataclass
class AnalysisContext:
    """Context information for better field analysis"""
    object_name: str
    field_name: str
    common_abbreviations: Dict[str, str]
    org_specific_terms: Dict[str, str]
    similar_fields: List[str]
    contextual_info: str = ""  # User-provided contextual information

class EnhancedAnalysisService:
    """
    Enhanced analysis service with intelligent model selection, 
    better confidence scoring, and context-aware analysis.
    """

    def __init__(self, api_key: str = None):
        """Initialize the enhanced analysis service."""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.use_real_api = bool(self.api_key and self.api_key != 'your_gemini_api_key' and len(self.api_key) > 10)
        
        # Initialize Google AI client
        if self.use_real_api:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.genai = genai  # Fix: Store genai on self
                self.client = self.genai.GenerativeModel('gemini-2.5-flash-lite')  # Default to top model
                self.model_name = 'gemini-2.5-flash-lite'
                logger.info("Enhanced AnalysisService initialized with Gemini API.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API: {e}. Falling back to mock responses.")
                self.use_real_api = False
                self.client = None
                self.genai = None
        else:
            logger.info("Enhanced AnalysisService initialized with mock responses.")
            self.client = None
            self.genai = None
        
        # Model selection strategy based on a priority list
        self.model_priority_list = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]
        
        # Quota management
        self.request_count = 0
        self.quota_limit = 1000  # Daily quota limit
        
        # Context database for better analysis
        self.common_abbreviations = {
            "AC": "Attempted Contact",
            "WAC": "WhatsApp Callback", 
            "MQL": "Marketing Qualified Lead",
            "SQL": "Sales Qualified Lead",
            "POC": "Proof of Concept",
            "ROI": "Return on Investment",
            "SLA": "Service Level Agreement",
            "CRM": "Customer Relationship Management",
            "API": "Application Programming Interface",
            "URL": "Uniform Resource Locator",
            "ID": "Identifier",
            "UUID": "Universally Unique Identifier",
            "CTR": "Click Through Rate",
            "CAC": "Customer Acquisition Cost",
            "LTV": "Lifetime Value",
            "NPS": "Net Promoter Score"
        }

    def _determine_field_complexity(self, field_metadata: dict, object_name: str) -> ModelCapability:
        """Determine the complexity level of a field for appropriate model selection."""
        field_name = field_metadata.get('name', '')
        field_label = field_metadata.get('label', '')
        is_custom = field_metadata.get('custom', False)
        has_help_text = bool(field_metadata.get('inlineHelpText'))
        
        # Simple cases - use lightweight model
        if not is_custom:  # Standard fields
            return ModelCapability.SIMPLE
            
        if has_help_text and len(field_metadata.get('inlineHelpText', '')) > 20:
            return ModelCapability.SIMPLE  # Clear help text available
            
        # Check for obvious patterns
        if any(pattern in field_name.lower() for pattern in ['email', 'phone', 'date', 'amount', 'count', 'flag', 'status']):
            return ModelCapability.SIMPLE
            
        # Medium complexity - common custom fields
        if len(field_name.split('_')) <= 3:  # Simple naming
            return ModelCapability.MEDIUM
            
        # Complex cases - need advanced reasoning
        # Abbreviations that might need context
        if any(abbrev in field_name for abbrev in ['AC', 'WAC', 'POC', 'ROI', 'MQL', 'SQL']):
            return ModelCapability.COMPLEX
            
        # Very long or complex field names
        if len(field_name) > 30 or len(field_name.split('_')) > 4:
            return ModelCapability.COMPLEX
            
        return ModelCapability.MEDIUM

    def _get_analysis_context(self, field_metadata: dict, object_name: str) -> AnalysisContext:
        """Build context for better field analysis."""
        field_name = field_metadata.get('name', '')
        
        # Extract potential abbreviations from field name
        context_abbrevs = {}
        for abbrev, meaning in self.common_abbreviations.items():
            if abbrev in field_name:
                context_abbrevs[abbrev] = meaning
                
        return AnalysisContext(
            object_name=object_name,
            field_name=field_name,
            common_abbreviations=context_abbrevs,
            org_specific_terms={},  # Could be populated from org analysis
            similar_fields=[]  # Could be populated from existing field analysis
        )

    def _construct_enhanced_prompt(self, field_metadata: dict, object_name: str, context: AnalysisContext) -> str:
        """Construct an enhanced prompt with context awareness."""
        
        prompt_data = {
            "objectApiName": object_name,
            "fieldApiName": field_metadata.get('name'),
            "label": field_metadata.get('label'),
            "dataType": field_metadata.get('type'),
            "length": field_metadata.get('length'),
            "isCustom": field_metadata.get('custom'),
            "existingHelpText": field_metadata.get('inlineHelpText'),
        }

        context_section = ""
        if context.common_abbreviations:
            context_section = f"""
        
        IMPORTANT CONTEXT - Common abbreviations in this field name:
        {json.dumps(context.common_abbreviations, indent=2)}
        
        Use these definitions when analyzing the field name. Do NOT make assumptions about abbreviations.
        """

        prompt = f"""
        You are a Salesforce expert analyzing field metadata. Analyze the following field and provide a business-oriented description.

        Field Information:
        {json.dumps(prompt_data, indent=2)}
        {context_section}

        Analysis Instructions:
        1. If this is a custom field (API name ends with __c), analyze its likely business purpose
        2. Use the provided abbreviation context - do NOT guess what abbreviations mean
        3. If you're making assumptions about unclear parts, LOWER your confidence score significantly
        4. If the field name contains abbreviations not in the context, mention this uncertainty
        5. Focus on WHY this field exists from a business perspective
        6. Be honest about uncertainty - it's better to have lower confidence than incorrect assumptions

        Confidence Scoring Guidelines:
        - 9-10: Field purpose is completely clear from name, label, type, and context
        - 7-8: Field purpose is mostly clear with minor assumptions
        - 5-6: Some assumptions made, but reasonable inference possible
        - 3-4: Significant assumptions made, field purpose is unclear
        - 1-2: Field purpose is very unclear, mostly guessing

        Respond with ONLY a JSON object containing:
        {{
            "description": "Clear, business-focused description of what this field is used for",
            "confidence_score": 6.5,
            "assumptions_made": ["list", "of", "assumptions", "if", "any"],
            "uncertainty_notes": "Any unclear aspects of the field"
        }}
        """
        
        return prompt.strip()

    def _call_llm_api_with_fallback(self, prompt: str) -> dict:
        """Call LLM API by iterating through the model priority list."""
        if not self.use_real_api:
            return self._mock_response()
            
        if self.request_count >= self.quota_limit:
            logger.warning("API quota exceeded, using fallback response")
            return self._quota_exceeded_response()
            
        for model_name in self.model_priority_list:
            try:
                logger.info(f"Attempting analysis with model: {model_name}")
                model = self.genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                self.request_count += 1
                logger.info(f"Successfully used model {model_name} for analysis (request #{self.request_count})")
                
                # Parse JSON response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    
                    # Validate and adjust confidence based on assumptions
                    assumptions = result.get('assumptions_made', [])
                    if assumptions and len(assumptions) > 0:
                        # Lower confidence if assumptions were made
                        current_confidence = result.get('confidence_score', 5.0)
                        adjusted_confidence = max(1.0, current_confidence - (len(assumptions) * 0.5))
                        result['confidence_score'] = adjusted_confidence
                        result['needs_review'] = adjusted_confidence < 7.0
                        logger.info(f"Adjusted confidence from {current_confidence} to {adjusted_confidence} due to {len(assumptions)} assumptions")
                    
                    return result
                else:
                    return {
                        "description": response_text,
                        "confidence_score": 6.0,
                        "assumptions_made": [],
                        "uncertainty_notes": "Raw response without structured format"
                    }
            
            except Exception as e:
                logger.error(f"Error with {model_name}: {e}. Trying next model in the list.")
                continue
        
        logger.error("All models in the priority list failed for the request.")
        return self._error_response("All available models failed analysis.")

    def _mock_response(self) -> dict:
        """Mock response for testing."""
        return {
            "description": "Mock AI-generated description. Set GOOGLE_API_KEY for real analysis.",
            "confidence_score": 5.0,
            "assumptions_made": [],
            "uncertainty_notes": "Mock response"
        }

    def _quota_exceeded_response(self) -> dict:
        """Response when API quota is exceeded."""
        return {
            "description": "Analysis unavailable - API quota exceeded. Please try again tomorrow or upgrade quota.",
            "confidence_score": 0.0,
            "assumptions_made": ["quota_exceeded"],
            "uncertainty_notes": "API quota limit reached"
        }

    def _error_response(self, error_msg: str) -> dict:
        """Response for API errors."""
        return {
            "description": f"Analysis failed: {error_msg}",
            "confidence_score": 0.0,
            "assumptions_made": ["api_error"],
            "uncertainty_notes": f"API error: {error_msg}"
        }

    def analyze_field(self, field_metadata: dict, object_name: str) -> dict:
        """
        Enhanced field analysis with intelligent model selection and better confidence scoring.
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
                "confidence_score": 10.0,
                "needs_review": False,
                "assumptions_made": [],
                "uncertainty_notes": ""
            }

        # Rule 2: Standard field without description - MEDIUM confidence
        if not is_custom and not description:
            logger.debug(f"Standard field {object_name}.{field_name} has no description")
            return {
                "description": f"Standard Salesforce field. {field_metadata.get('label', field_name)} is a built-in field for {object_name} objects.",
                "source": "Salesforce", 
                "confidence_score": 8.0,
                "needs_review": False,
                "assumptions_made": [],
                "uncertainty_notes": ""
            }

        # Rule 3: Custom field - enhanced analysis
        logger.info(f"Analyzing custom field {object_name}.{field_name} with enhanced service")
        
        # Determine complexity and context
        context = self._get_analysis_context(field_metadata, object_name)
        
        # Construct enhanced prompt
        prompt = self._construct_enhanced_prompt(field_metadata, object_name, context)
        
        try:
            llm_result = self._call_llm_api_with_fallback(prompt)
            confidence = llm_result.get('confidence_score', 5.0)
            
            return {
                "description": llm_result.get('description', 'Analysis failed - no description returned.'),
                "source": "Enhanced-Gemini" if self.use_real_api else "Mock",
                "confidence_score": confidence,
                "needs_review": confidence < 7.0,
                "assumptions_made": llm_result.get('assumptions_made', []),
                "uncertainty_notes": llm_result.get('uncertainty_notes', "")
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze field with enhanced LLM: {e}")
            return {
                "description": "Analysis failed due to an error.",
                "source": "Error",
                "confidence_score": 0.0,
                "needs_review": True,
                "assumptions_made": ["analysis_error"],
                "uncertainty_notes": f"Error: {str(e)}"
            }

    def get_quota_status(self) -> dict:
        """Get current quota usage status."""
        return {
            "requests_used": self.request_count,
            "quota_limit": self.quota_limit,
            "remaining": max(0, self.quota_limit - self.request_count),
            "percentage_used": (self.request_count / self.quota_limit) * 100,
            "current_model_fallback_index": self.current_model_index
        }

    def batch_analyze_fields(self, fields_metadata: List[dict], object_name: str) -> List[dict]:
        """
        Analyze multiple fields by iterating and calling the single-field analysis method.
        """
        results = []
        logger.info(f"Starting batch analysis for {len(fields_metadata)} fields.")

        for field_meta in fields_metadata:
            if self.request_count >= self.quota_limit:
                logger.warning("Quota limit reached during batch processing. Aborting.")
                break
                
            result = self.analyze_field(field_meta, object_name)
            results.append(result)
            
            # Add small delay to avoid rate limiting
            if self.use_real_api:
                time.sleep(0.1)
        
        return results

    def analyze_field_with_context(self, field_metadata: dict, object_name: str, contextual_info: str) -> dict:
        """
        Enhanced field analysis with user-provided contextual information.
        """
        try:
            # Get base complexity and context
            context = self._get_analysis_context(field_metadata, object_name)
            
            # Add user-provided context to the existing context
            context.contextual_info = contextual_info
            
            # Build enhanced prompt with user context
            enhanced_prompt = self._construct_contextual_prompt(field_metadata, object_name, context, contextual_info)
            
            # Call LLM with contextual prompt
            result = self._call_llm_api_with_fallback(enhanced_prompt)
            
            # Add contextual analysis metadata
            result['source'] = 'ai_generated'
            result['contextual_analysis'] = True
            result['user_context'] = contextual_info[:200]  # Store first 200 chars
            
            return result
            
        except Exception as e:
            logger.error(f"Error in contextual analysis for {field_metadata.get('name', 'unknown')}: {e}")
            return {
                'description': f"Contextual analysis failed: {str(e)}",
                'confidence_score': 0.0,
                'needs_review': True,
                'source': 'ai_generated',
                'assumptions_made': [],
                'uncertainty_notes': f"Failed to analyze with context: {contextual_info[:100]}"
            }

    def _construct_contextual_prompt(self, field_metadata: dict, object_name: str, context: AnalysisContext, user_context: str) -> str:
        """
        Construct an enhanced prompt that incorporates user-provided contextual information.
        """
        field_name = field_metadata.get('name', 'Unknown')
        field_label = field_metadata.get('label', '')
        field_type = field_metadata.get('type', 'Unknown')
        is_custom = field_metadata.get('custom', False)
        
        prompt = f"""You are analyzing the Salesforce field '{field_name}' on the {object_name} object.

FIELD DETAILS:
- API Name: {field_name}
- Label: {field_label}
- Type: {field_type}
- Custom Field: {is_custom}

USER-PROVIDED CONTEXT:
{user_context}

IMPORTANT: Use the user-provided context above to inform your analysis. This context contains domain-specific knowledge that should guide your understanding of the field's purpose and usage.

Your task is to provide a comprehensive description of this field's purpose, usage, and business context, incorporating the user-provided information.

ANALYSIS REQUIREMENTS:
1. Start with the user-provided context as the foundation for your analysis
2. Explain how this field is likely used in business processes
3. Describe what values it might contain and why
4. Note any relationships to other fields or objects
5. Consider data quality, compliance, or operational implications

CONFIDENCE SCORING:
- Score 9-10: User context provides clear, specific information about the field
- Score 7-8: User context gives good insights, some details inferred
- Score 5-6: User context helpful but requires some assumptions
- Score 3-4: Limited context, significant assumptions needed
- Score 1-2: Context unclear or contradictory

If you make assumptions beyond the user-provided context, list them explicitly.
If anything is uncertain despite the context, note it clearly.

Respond in this JSON format:
{{"description": "detailed field description", "confidence_score": 8.5, "assumptions_made": ["list", "of", "assumptions"], "uncertainty_notes": "any uncertainties"}}"""

        return prompt 

    def analyze_fields_batch(self, batch_prompt: str, fields: List[dict]) -> dict:
        """Analyze multiple fields in a single AI request with model fallback."""
        if not self.use_real_api or not self.genai:
            logger.warning("Client not available, falling back to mock responses")
            # Return mock results for all fields
            return {
                'field_analyses': [
                    {
                        'description': f"Mock analysis for {field.get('field_name', 'unknown')}",
                        'confidence_score': 5.0,
                        'assumptions_made': ['mock_response'],
                        'uncertainty_notes': 'This is a mock response (no API key configured)'
                    } for field in fields
                ],
                'batch_size': len(fields),
                'source': 'mock'
            }

        for model_name in self.model_priority_list:
            try:
                logger.info(f"🚀 Batch analyzing {len(fields)} fields with model: {model_name}...")
                
                model = self.genai.GenerativeModel(model_name)
                response = model.generate_content(
                    batch_prompt,
                    generation_config=self.genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=4000  # Allow longer output for multiple fields
                    )
                )
                
                self.request_count += 1
                logger.info(f"Successfully used model {model_name} for batch analysis (request #{self.request_count})")
                
                # Parse JSON response
                try:
                    result = json.loads(response.text)
                    
                    # Validate and enhance results
                    field_analyses = result.get('field_analyses', [])
                    
                    # Ensure we have results for all fields
                    while len(field_analyses) < len(fields):
                        field_analyses.append({
                            "field_name": fields[len(field_analyses)].get('field_name', 'unknown'),
                            "description": "Unable to analyze in batch mode",
                            "confidence_score": 3.0,
                            "needs_review": True,
                            "reasoning": "Batch analysis incomplete"
                        })
                    
                    # Apply confidence adjustments based on assumptions
                    for analysis in field_analyses:
                        reasoning = analysis.get('reasoning', '')
                        assumption_indicators = ['assume', 'likely', 'probably', 'might', 'could be', 'appears to']
                        assumption_count = sum(1 for indicator in assumption_indicators if indicator in reasoning.lower())
                        
                        if assumption_count > 0:
                            original_confidence = analysis.get('confidence_score', 6.0)
                            adjusted_confidence = max(2.0, original_confidence - (assumption_count * 0.8))
                            analysis['confidence_score'] = round(adjusted_confidence, 1)
                            logger.debug(f"Adjusted confidence from {original_confidence} to {adjusted_confidence} due to {assumption_count} assumptions")
                    
                    logger.info(f"✅ Batch analysis completed for {len(field_analyses)} fields")
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.error(f"Failed to parse batch analysis JSON from {model_name}: {je}")
                    logger.error(f"Raw response: {response.text[:500]}...")
                    # Continue to try the next model
                    continue
            
            except Exception as e:
                logger.error(f"Batch analysis with model {model_name} failed: {e}. Trying next model.")
                continue

        logger.error("All models failed for batch analysis.")
        # Fallback results if all models fail
        return {
            "field_analyses": [
                {
                    "field_name": field.get('field_name', 'unknown'),
                    "description": f"Analysis failed for {field.get('field_name', 'unknown')} with all models.",
                    "confidence_score": 1.0,
                    "needs_review": True,
                    "reasoning": "All models in the priority list failed."
                } for field in fields
            ]
        } 