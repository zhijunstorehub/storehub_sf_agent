import subprocess
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Extracts metadata from a Salesforce org using the 'sf' CLI.
    """

    def __init__(self, org_alias: str):
        """
        Initializes the MetadataExtractor.

        Args:
            org_alias (str): The alias of the target Salesforce org.
        """
        self.org_alias = org_alias
        self._check_sf_cli_auth()

    def _run_command(self, command: list) -> dict:
        """
        Executes a command and returns the JSON output.

        Args:
            command (list): The command to execute as a list of strings.

        Returns:
            dict: The JSON output from the command.
            
        Raises:
            RuntimeError: If the command fails or returns non-JSON output.
        """
        logger.info(f"Executing command: {' '.join(command)}")
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,  # Raises CalledProcessError for non-zero exit codes
                encoding='utf-8'
            )
            return json.loads(process.stdout)
        except subprocess.CalledProcessError as e:
            error_message = f"Command failed with exit code {e.returncode}.\n"
            error_message += f"Stderr: {e.stderr}\n"
            error_message += f"Stdout: {e.stdout}"
            logger.error(error_message)
            raise RuntimeError(error_message) from e
        except json.JSONDecodeError as e:
            error_message = f"Failed to decode JSON from command output: {e}"
            logger.error(error_message)
            raise RuntimeError(error_message) from e
        except FileNotFoundError:
            error_message = "The 'sf' command-line tool is not installed or not in the system's PATH. Please install it to continue."
            logger.error(error_message)
            raise RuntimeError(error_message)

    def _check_sf_cli_auth(self):
        """Checks if the user is authenticated to the target org."""
        try:
            self._run_command(['sf', 'org', 'display', '-o', self.org_alias, '--json'])
            logger.info(f"Successfully authenticated to Salesforce org: {self.org_alias}")
        except RuntimeError:
            logger.error(f"Authentication check failed for org '{self.org_alias}'. Please ensure you are logged in via 'sf login'.")
            raise

    def list_all_sobjects(self) -> list:
        """
        Lists all SObject API names in the org.

        Returns:
            list: A list of SObject API names.
        """
        logger.info("Fetching list of all SObjects...")
        command = ['sf', 'sobject', 'list', '--sobject', 'all', '-o', self.org_alias, '--json']
        result = self._run_command(command)
        
        # The 'sf sobject list' command returns a list of strings under the 'result' key.
        sobject_names = result.get('result', [])
        logger.info(f"Found {len(sobject_names)} SObjects.")
        return sobject_names

    def describe_sobject(self, sobject_name: str) -> dict:
        """
        Retrieves the metadata for a specific SObject.

        Args:
            sobject_name (str): The API name of the SObject to describe.

        Returns:
            dict: The detailed metadata of the SObject.
        """
        logger.info(f"Describing SObject: {sobject_name}...")
        command = ['sf', 'sobject', 'describe', '-s', sobject_name, '-o', self.org_alias, '--json']
        result = self._run_command(command)
        
        # The 'sf sobject describe' command returns the object metadata under the 'result' key.
        return result.get('result', {})

# Example of how to use the service
if __name__ == '__main__':
    # This block is for demonstration and testing purposes.
    # It will run when the script is executed directly.
    # IMPORTANT: You must be logged into a Salesforce org with the alias 'sandbox'
    # for this demonstration to work.
    logger.info("Running MetadataExtractor demonstration...")
    
    ORG_ALIAS = "sandbox" # Replace with your org alias if different
    
    try:
        extractor = MetadataExtractor(org_alias=ORG_ALIAS)
        
        # 1. List some SObjects (we'll take just the first 5 for the demo)
        all_sobjects = extractor.list_all_sobjects()
        if not all_sobjects:
            logger.warning("No SObjects found. The org might be empty or there was an issue.")
        else:
            demo_sobjects = all_sobjects[:5]
            logger.info(f"Will describe the first 5 SObjects: {demo_sobjects}")

            # 2. Describe each of the demo SObjects
            for sobject in demo_sobjects:
                description = extractor.describe_sobject(sobject)
                if description:
                    field_count = len(description.get('fields', []))
                    logger.info(f"Successfully described '{sobject}'. It has {field_count} fields.")
                    # print(json.dumps(description, indent=2)) # Uncomment to see full detail
                else:
                    logger.warning(f"Could not get a description for '{sobject}'.")

    except RuntimeError as e:
        logger.error(f"An error occurred during the demonstration: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
