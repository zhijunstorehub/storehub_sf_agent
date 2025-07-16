"""
Salesforce API client with robust connection management and error handling.
"""

import logging
from typing import Dict, Any, Optional
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed, SalesforceError

from ..config import SalesforceConfig

logger = logging.getLogger(__name__)


class SalesforceConnectionError(Exception):
    """Custom exception for Salesforce connection issues."""
    pass


class SalesforceClient:
    """
    Enhanced Salesforce API client with connection management and error handling.
    
    This client provides a robust interface to Salesforce APIs, handling authentication,
    connection management, and providing clear error messages for troubleshooting.
    """
    
    def __init__(self, config: SalesforceConfig):
        """Initialize Salesforce client with configuration."""
        self.config = config
        self._sf_client: Optional[Salesforce] = None
        
    def connect(self) -> None:
        """
        Establish connection to Salesforce with comprehensive error handling.
        
        Raises:
            SalesforceConnectionError: If connection fails with detailed error message
        """
        try:
            logger.info(f"Connecting to Salesforce domain: {self.config.domain}")
            
            self._sf_client = Salesforce(
                username=self.config.username,
                password=self.config.password,
                security_token=self.config.security_token,
                domain=self.config.domain,
                client_id=self.config.consumer_key,
            )
            
            # Test connection with a simple query
            self._sf_client.query("SELECT Id FROM Organization LIMIT 1")
            logger.info("Successfully connected to Salesforce")
            
        except SalesforceAuthenticationFailed as e:
            error_msg = self._format_auth_error(str(e))
            logger.error(f"Salesforce authentication failed: {error_msg}")
            raise SalesforceConnectionError(error_msg) from e
            
        except SalesforceError as e:
            error_msg = f"Salesforce API error: {str(e)}"
            logger.error(error_msg)
            raise SalesforceConnectionError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error connecting to Salesforce: {str(e)}"
            logger.error(error_msg)
            raise SalesforceConnectionError(error_msg) from e
    
    def _format_auth_error(self, error_message: str) -> str:
        """Format authentication error with helpful troubleshooting guidance."""
        base_msg = f"Authentication failed: {error_message}"
        
        troubleshooting = """
        
Troubleshooting steps:
1. Verify your username and password are correct
2. Check if your security token is valid (you may need to reset it)
3. Ensure the domain is correct: {domain}
4. If using IP restrictions, verify your IP is whitelisted
5. Check if your user has API access enabled

Security Token Reset:
- Go to Setup → My Personal Information → Reset My Security Token
- Check your email for the new security token
        """.format(domain=self.config.domain)
        
        return base_msg + troubleshooting
    
    @property
    def client(self) -> Salesforce:
        """
        Get the Salesforce client instance.
        
        Returns:
            Salesforce client instance
            
        Raises:
            SalesforceConnectionError: If not connected
        """
        if self._sf_client is None:
            raise SalesforceConnectionError(
                "Not connected to Salesforce. Call connect() first."
            )
        return self._sf_client
    
    def is_connected(self) -> bool:
        """Check if client is connected to Salesforce."""
        return self._sf_client is not None
    
    def get_org_info(self) -> Dict[str, Any]:
        """
        Get basic organization information for verification.
        
        Returns:
            Dictionary containing org information
        """
        result = self.client.query(
            "SELECT Id, Name, OrganizationType, InstanceName FROM Organization"
        )
        
        if result["totalSize"] > 0:
            org = result["records"][0]
            return {
                "org_id": org["Id"],
                "org_name": org["Name"],
                "org_type": org["OrganizationType"],
                "instance": org["InstanceName"],
            }
        return {}
    
    def test_connection(self) -> bool:
        """
        Test the Salesforce connection.
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            self.get_org_info()
            logger.info("Salesforce connection test successful")
            return True
        except Exception as e:
            logger.error(f"Salesforce connection test failed: {e}")
            return False 