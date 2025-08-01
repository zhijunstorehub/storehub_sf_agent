"""
Salesforce Documentation Extractor

This service extracts rich field descriptions from the official Salesforce Object Reference
documentation, providing more comprehensive and business-context aware descriptions
than what's available through the Salesforce API.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class SalesforceDocsExtractor:
    """
    Extracts field descriptions from official Salesforce Object Reference documentation.
    """
    
    BASE_URL = "https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/"
    
    # Mapping of common object names to their documentation URLs
    OBJECT_DOC_MAPPING = {
        'Account': 'sforce_api_objects_account.htm',
        'Contact': 'sforce_api_objects_contact.htm', 
        'Lead': 'sforce_api_objects_lead.htm',
        'Opportunity': 'sforce_api_objects_opportunity.htm',
        'Case': 'sforce_api_objects_case.htm',
        'Campaign': 'sforce_api_objects_campaign.htm',
        'User': 'sforce_api_objects_user.htm',
        'Task': 'sforce_api_objects_task.htm',
        'Event': 'sforce_api_objects_event.htm'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._rate_limit_delay = 1.0  # 1 second between requests
    
    def get_object_field_descriptions(self, object_name: str) -> Dict[str, Dict]:
        """
        Extract all field descriptions for a given Salesforce object from official docs.
        
        Args:
            object_name: Name of the Salesforce object (e.g., 'Account', 'Lead')
            
        Returns:
            Dictionary mapping field names to their description data
        """
        if object_name not in self.OBJECT_DOC_MAPPING:
            logger.warning(f"No documentation mapping found for object: {object_name}")
            return {}
        
        doc_url = urljoin(self.BASE_URL, self.OBJECT_DOC_MAPPING[object_name])
        
        try:
            logger.info(f"Extracting field descriptions for {object_name} from {doc_url}")
            
            # Add rate limiting
            time.sleep(self._rate_limit_delay)
            
            response = self.session.get(doc_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            field_descriptions = self._parse_field_descriptions(soup, object_name)
            
            logger.info(f"Successfully extracted {len(field_descriptions)} field descriptions for {object_name}")
            return field_descriptions
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch documentation for {object_name}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing documentation for {object_name}: {e}")
            return {}
    
    def _parse_field_descriptions(self, soup: BeautifulSoup, object_name: str) -> Dict[str, Dict]:
        """
        Parse field descriptions from the Salesforce documentation HTML.
        
        Args:
            soup: BeautifulSoup object of the documentation page
            object_name: Name of the object being parsed
            
        Returns:
            Dictionary mapping field names to description data
        """
        field_descriptions = {}
        
        # Strategy 1: Look for field tables (most common format)
        field_descriptions.update(self._parse_field_table(soup))
        
        # Strategy 2: Look for individual field sections
        field_descriptions.update(self._parse_field_sections(soup))
        
        # Strategy 3: Look for definition lists
        field_descriptions.update(self._parse_definition_lists(soup))
        
        return field_descriptions
    
    def _parse_field_table(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Parse fields from table format (most common in Salesforce docs)."""
        field_descriptions = {}
        
        # Look for tables containing field information
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            # Find header row to identify column positions
            header_row = None
            field_col = desc_col = type_col = props_col = -1
            
            for i, row in enumerate(rows):
                headers = row.find_all(['th', 'td'])
                if len(headers) >= 2:
                    header_texts = [h.get_text().strip().lower() for h in headers]
                    
                    # Look for field-related headers
                    if any(keyword in ' '.join(header_texts) for keyword in ['field', 'name', 'description']):
                        header_row = i
                        
                        # Identify column positions
                        for j, header_text in enumerate(header_texts):
                            if 'field' in header_text or 'name' in header_text:
                                field_col = j
                            elif 'description' in header_text:
                                desc_col = j
                            elif 'type' in header_text:
                                type_col = j
                            elif 'properties' in header_text:
                                props_col = j
                        break
            
            # Parse data rows
            if header_row is not None and field_col >= 0 and desc_col >= 0:
                for row in rows[header_row + 1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > max(field_col, desc_col):
                        field_name = cells[field_col].get_text().strip()
                        description = cells[desc_col].get_text().strip()
                        
                        if field_name and description and len(description) > 10:
                            field_data = {
                                'description': description,
                                'source': 'Salesforce Object Reference',
                                'confidence_score': 10.0
                            }
                            
                            # Add type information if available
                            if type_col >= 0 and len(cells) > type_col:
                                field_data['field_type'] = cells[type_col].get_text().strip()
                            
                            # Add properties if available
                            if props_col >= 0 and len(cells) > props_col:
                                field_data['properties'] = cells[props_col].get_text().strip()
                            
                            field_descriptions[field_name] = field_data
        
        return field_descriptions
    
    def _parse_field_sections(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Parse fields from individual section format."""
        field_descriptions = {}
        
        # Look for sections with field names as headers
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            heading_text = heading.get_text().strip()
            
            # Skip if this doesn't look like a field name
            if not heading_text or len(heading_text) > 50:
                continue
                
            # Look for description in following elements
            description_parts = []
            current = heading.next_sibling
            
            while current and len(description_parts) < 3:
                if hasattr(current, 'name'):
                    if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                    elif current.name in ['p', 'div']:
                        text = current.get_text().strip()
                        if text and len(text) > 10:
                            description_parts.append(text)
                current = current.next_sibling
            
            if description_parts:
                description = ' '.join(description_parts)
                field_descriptions[heading_text] = {
                    'description': description,
                    'source': 'Salesforce Object Reference',
                    'confidence_score': 9.0
                }
        
        return field_descriptions
    
    def _parse_definition_lists(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Parse fields from definition list format."""
        field_descriptions = {}
        
        # Look for definition lists (dt/dd pairs)
        dls = soup.find_all('dl')
        
        for dl in dls:
            terms = dl.find_all('dt')
            definitions = dl.find_all('dd')
            
            # Pair up terms and definitions
            for i in range(min(len(terms), len(definitions))):
                term = terms[i].get_text().strip()
                definition = definitions[i].get_text().strip()
                
                if term and definition and len(definition) > 10:
                    field_descriptions[term] = {
                        'description': definition,
                        'source': 'Salesforce Object Reference',
                        'confidence_score': 9.5
                    }
        
        return field_descriptions
    
    def get_field_description(self, object_name: str, field_name: str) -> Optional[Dict]:
        """
        Get description for a specific field from official documentation.
        
        Args:
            object_name: Name of the Salesforce object
            field_name: Name of the field
            
        Returns:
            Dictionary with field description data or None if not found
        """
        all_fields = self.get_object_field_descriptions(object_name)
        return all_fields.get(field_name)
    
    def update_database_with_official_descriptions(self, db_service, object_name: str, force_update: bool = False) -> Dict:
        """
        Update database with official descriptions from Salesforce documentation.
        
        Args:
            db_service: Database service instance
            object_name: Object to update descriptions for
            force_update: Whether to update existing descriptions
            
        Returns:
            Dictionary with update results
        """
        results = {
            'status': 'success',
            'object_name': object_name,
            'updated_count': 0,
            'skipped_count': 0,
            'errors': []
        }
        
        try:
            # Get official descriptions
            official_descriptions = self.get_object_field_descriptions(object_name)
            
            if not official_descriptions:
                results['status'] = 'no_data'
                results['message'] = f"No official documentation found for {object_name}"
                return results
            
            # Update each field
            for field_name, field_data in official_descriptions.items():
                try:
                    # Check if field exists in database
                    existing_field = db_service.get_metadata_by_field(object_name, field_name)
                    
                    if existing_field:
                        # Check if we should update
                        should_update = (
                            force_update or 
                            not existing_field.get('description') or
                            existing_field.get('source') != 'Salesforce Object Reference'
                        )
                        
                        if should_update:
                            success = db_service.update_field_description(
                                object_name=object_name,
                                field_name=field_name,
                                new_description=field_data['description'],
                                confidence_score=field_data['confidence_score']
                            )
                            
                            if success:
                                results['updated_count'] += 1
                            else:
                                results['errors'].append(f"Failed to update {field_name}")
                        else:
                            results['skipped_count'] += 1
                    else:
                        # Field doesn't exist in database, create new record
                        record = {
                            'object_name': object_name,
                            'field_name': field_name,
                            'field_label': field_name,  # Will be updated by API call later
                            'field_type': field_data.get('field_type', 'unknown'),
                            'is_custom': False,  # Official docs are for standard fields
                            'description': field_data['description'],
                            'source': field_data['source'],
                            'confidence_score': field_data['confidence_score'],
                            'needs_review': False,
                            'raw_metadata': str(field_data)
                        }
                        
                        db_service.upsert_metadata_record(record)
                        results['updated_count'] += 1
                        
                except Exception as e:
                    error_msg = f"Error updating field {field_name}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            logger.info(f"Updated {results['updated_count']} fields for {object_name} from official docs")
            
        except Exception as e:
            results['status'] = 'error'
            results['message'] = f"Failed to update {object_name}: {str(e)}"
            logger.error(f"Error updating {object_name} with official descriptions: {e}")
        
        return results 