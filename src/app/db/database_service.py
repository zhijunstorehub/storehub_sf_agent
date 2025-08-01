import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Handles all database operations for the Salesforce metadata.
    """

    def __init__(self, db_path='salesforce_metadata.db'):
        """
        Initializes the DatabaseService and connects to the SQLite database.

        Args:
            db_path (str): The path to the SQLite database file.
        """
        # Ensure the database directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        try:
            # Add check_same_thread=False for FastAPI compatibility
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to database at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

    def create_metadata_table(self):
        """
        Creates the 'salesforce_metadata' table if it doesn't already exist.
        The schema is designed to be flexible for future enhancements.
        """
        try:
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS salesforce_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        object_name TEXT NOT NULL,
                        field_name TEXT NOT NULL,
                        field_label TEXT,
                        field_type TEXT,
                        is_custom BOOLEAN NOT NULL,
                        description TEXT,
                        source TEXT,
                        confidence_score REAL,
                        needs_review BOOLEAN,
                        raw_metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(object_name, field_name)
                    )
                """)
                
                # Create field history table for tracking changes
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS field_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metadata_id INTEGER NOT NULL,
                        object_name TEXT NOT NULL,
                        field_name TEXT NOT NULL,
                        field_description_old TEXT,
                        field_description_new TEXT,
                        confidence_score_old REAL,
                        confidence_score_new REAL,
                        change_type TEXT NOT NULL,  -- 'description', 'confidence', 'both'
                        changed_by TEXT DEFAULT 'system',
                        change_reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (metadata_id) REFERENCES salesforce_metadata (id)
                    )
                """)
                
                logger.info("'salesforce_metadata' and 'field_history' tables created or already exist.")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def upsert_metadata_record(self, record: dict):
        """
        Inserts a new metadata record or updates it if it already exists.
        Uses the composite key (object_name, field_name) to check for existence.

        Args:
            record (dict): A dictionary containing the metadata to be saved.
        """
        sql = """
            INSERT INTO salesforce_metadata (
                object_name, field_name, field_label, field_type, is_custom, 
                description, source, confidence_score, needs_review, raw_metadata
            ) VALUES (:object_name, :field_name, :field_label, :field_type, :is_custom, 
                      :description, :source, :confidence_score, :needs_review, :raw_metadata)
            ON CONFLICT(object_name, field_name) DO UPDATE SET
                field_label=excluded.field_label,
                field_type=excluded.field_type,
                is_custom=excluded.is_custom,
                description=excluded.description,
                source=excluded.source,
                confidence_score=excluded.confidence_score,
                needs_review=excluded.needs_review,
                raw_metadata=excluded.raw_metadata,
                updated_at=CURRENT_TIMESTAMP
        """
        try:
            with self.conn:
                self.conn.execute(sql, record)
            logger.debug(f"Upserted record for {record.get('object_name')}.{record.get('field_name')}")
        except sqlite3.Error as e:
            logger.error(f"Error upserting record for {record.get('object_name')}.{record.get('field_name')}: {e}")
            raise

    def get_all_metadata(self, limit: int = None, offset: int = 0) -> list:
        """
        Retrieves all metadata records with optional pagination.

        Args:
            limit (int, optional): Maximum number of records to return.
            offset (int): Number of records to skip for pagination.

        Returns:
            list: A list of metadata records as dictionaries.
        """
        sql = "SELECT * FROM salesforce_metadata ORDER BY object_name, field_name"
        params = []
        
        if limit:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving metadata: {e}")
            raise

    def get_metadata_by_object(self, object_name: str) -> list:
        """
        Retrieves all metadata records for a specific object.

        Args:
            object_name (str): The API name of the object.

        Returns:
            list: A list of metadata records for the specified object.
        """
        sql = "SELECT * FROM salesforce_metadata WHERE object_name = ? ORDER BY field_name"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (object_name,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving metadata for object {object_name}: {e}")
            raise

    def get_metadata_by_field(self, object_name: str, field_name: str) -> dict:
        """
        Retrieves metadata for a specific field.

        Args:
            object_name (str): The API name of the object.
            field_name (str): The API name of the field.

        Returns:
            dict: The metadata record for the specified field, or None if not found.
        """
        sql = "SELECT * FROM salesforce_metadata WHERE object_name = ? AND field_name = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (object_name, field_name))
            row = cursor.fetchone()
            if row:
                record = dict(row)
                # Enhance with parsed metadata
                record['enhanced_metadata'] = self._parse_raw_metadata(record.get('raw_metadata'))
                return record
            return None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving metadata for {object_name}.{field_name}: {e}")
            raise

    def _parse_raw_metadata(self, raw_metadata: str) -> dict:
        """
        Parse the raw_metadata JSON field to extract additional field properties.

        Args:
            raw_metadata (str): JSON string containing raw field metadata

        Returns:
            dict: Parsed metadata with additional field properties
        """
        if not raw_metadata:
            return {}
        
        try:
            import json
            metadata = json.loads(raw_metadata)
            
            # Extract common Salesforce field properties
            enhanced = {
                'help_text': metadata.get('inlineHelpText', ''),
                'is_required': not metadata.get('nillable', True),
                'is_unique': metadata.get('unique', False),
                'length': metadata.get('length'),
                'precision': metadata.get('precision'),
                'scale': metadata.get('scale'),
                'default_value': metadata.get('defaultValue'),
                'relationship_name': metadata.get('relationshipName'),
                'reference_to': metadata.get('referenceTo', []),
                'calculated': metadata.get('calculated', False),
                'auto_number': metadata.get('autoNumber', False),
                'external_id': metadata.get('externalId', False),
                'case_sensitive': metadata.get('caseSensitive', False),
                'digits_left': metadata.get('digits'),
                'dependent_picklist': metadata.get('dependentPicklist', False),
                'encrypted': metadata.get('encrypted', False),
                'filterable': metadata.get('filterable', True),
                'groupable': metadata.get('groupable', True),
                'sortable': metadata.get('sortable', True),
                'queryable': metadata.get('queryable', True),
                'restricted_picklist': metadata.get('restrictedPicklist', False),
                'mask': metadata.get('mask'),
                'mask_type': metadata.get('maskType'),
                'picklist_values': self._extract_picklist_values(metadata),
                'display_location_in_decimal': metadata.get('displayLocationInDecimal', False),
                'html_formatted': metadata.get('htmlFormatted', False),
                'polymorphic_foreign_key': metadata.get('polymorphicForeignKey', False),
                'cascade_delete': metadata.get('cascadeDelete', False),
                'restricted_delete': metadata.get('restrictedDelete', False),
                'write_requires_master_read': metadata.get('writeRequiresMasterRead', False),
                'aggregatable': metadata.get('aggregatable', False),
                'ai_prediction_field': metadata.get('aiPredictionField', False),
                'search_prefilterable': metadata.get('searchPrefilterable', False),
                'extra_type_info': metadata.get('extraTypeInfo'),
                'compound_field_name': metadata.get('compoundFieldName'),
                'controlling_field_name': metadata.get('controllerName'),
                'formula': metadata.get('calculatedFormula'),
                'default_value_formula': metadata.get('defaultValueFormula'),
                'custom_setting': metadata.get('customSetting', False),
                'high_scale_number': metadata.get('highScaleNumber', False),
                'soap_type': metadata.get('soapType'),
            }
            
            # Remove None values to keep the response clean
            return {k: v for k, v in enhanced.items() if v is not None and v != ''}
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse raw metadata: {e}")
            return {}
    
    def _extract_picklist_values(self, field_metadata: dict) -> list:
        """Extract picklist values from field metadata."""
        picklist_values = []
        
        if field_metadata.get('picklistValues'):
            for value in field_metadata['picklistValues']:
                picklist_values.append({
                    'value': value.get('value'),
                    'label': value.get('label'),
                    'active': value.get('active', True),
                    'default_value': value.get('defaultValue', False),
                    'valid_for': value.get('validFor')
                })
        
        return picklist_values

    def get_records_needing_review(self) -> list:
        """
        Retrieves all metadata records that need manual review.

        Returns:
            list: A list of metadata records flagged for review.
        """
        sql = "SELECT * FROM salesforce_metadata WHERE needs_review = 1 ORDER BY confidence_score ASC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving records needing review: {e}")
            raise

    def get_objects_summary(self) -> list:
        """
        Retrieves a summary of all objects with field counts and review status.

        Returns:
            list: A list of object summaries.
        """
        sql = """
            SELECT 
                object_name,
                COUNT(*) as total_fields,
                SUM(CASE WHEN is_custom = 1 THEN 1 ELSE 0 END) as custom_fields,
                SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) as fields_needing_review,
                AVG(confidence_score) as avg_confidence_score
            FROM salesforce_metadata 
            GROUP BY object_name 
            ORDER BY object_name
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving objects summary: {e}")
            raise

    def update_field_description(self, object_name: str, field_name: str, new_description: str, confidence_score: float = None) -> bool:
        """
        Updates the description and confidence score for a specific field.
        Records the change in field_history table.

        Args:
            object_name (str): The API name of the object.
            field_name (str): The API name of the field.
            new_description (str): The new description.
            confidence_score (float, optional): The new confidence score.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            with self.conn:
                # Get current values first
                current_record = self.get_metadata_by_field(object_name, field_name)
                if not current_record:
                    return False
                
                old_description = current_record.get('description')
                old_confidence = current_record.get('confidence_score')
                
                # Determine change type
                change_type = []
                if old_description != new_description:
                    change_type.append('description')
                if confidence_score is not None and old_confidence != confidence_score:
                    change_type.append('confidence')
                
                if not change_type:
                    return True  # No changes needed
                
                change_type_str = '_'.join(change_type)
                needs_review = confidence_score < 7.0 if confidence_score is not None else False
                
                # Update the main record
                sql = """
                    UPDATE salesforce_metadata 
                    SET description = ?, confidence_score = ?, needs_review = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE object_name = ? AND field_name = ?
                """
                
                cursor = self.conn.execute(sql, (new_description, confidence_score, needs_review, object_name, field_name))
                if cursor.rowcount == 0:
                    return False
                
                # Record the change in history
                history_sql = """
                    INSERT INTO field_history (
                        metadata_id, object_name, field_name, 
                        field_description_old, field_description_new,
                        confidence_score_old, confidence_score_new,
                        change_type, change_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                self.conn.execute(history_sql, (
                    current_record['id'], object_name, field_name,
                    old_description, new_description,
                    old_confidence, confidence_score,
                    change_type_str, 'Manual update via UI'
                ))
                
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error updating field {object_name}.{field_name}: {e}")
            raise

    def get_field_history(self, object_name: str, field_name: str) -> list:
        """
        Retrieves the change history for a specific field.

        Args:
            object_name (str): The API name of the object.
            field_name (str): The API name of the field.

        Returns:
            list: A list of historical changes for the field.
        """
        sql = """
            SELECT * FROM field_history 
            WHERE object_name = ? AND field_name = ? 
            ORDER BY created_at DESC
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (object_name, field_name))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving field history for {object_name}.{field_name}: {e}")
            raise

    def revert_field_to_version(self, object_name: str, field_name: str, history_id: int) -> bool:
        """
        Reverts a field to a previous version based on history record.

        Args:
            object_name (str): The API name of the object.
            field_name (str): The API name of the field.
            history_id (int): The ID of the history record to revert to.

        Returns:
            bool: True if the revert was successful, False otherwise.
        """
        try:
            with self.conn:
                # Get the history record
                history_sql = "SELECT * FROM field_history WHERE id = ? AND object_name = ? AND field_name = ?"
                cursor = self.conn.cursor()
                cursor.execute(history_sql, (history_id, object_name, field_name))
                history_record = cursor.fetchone()
                
                if not history_record:
                    return False
                
                history_dict = dict(history_record)
                
                # Get current values
                current_record = self.get_metadata_by_field(object_name, field_name)
                if not current_record:
                    return False
                
                # Revert to old values from the history record
                old_description = history_dict['field_description_old']
                old_confidence = history_dict['confidence_score_old']
                
                needs_review = old_confidence < 7.0 if old_confidence is not None else False
                
                # Update the main record
                update_sql = """
                    UPDATE salesforce_metadata 
                    SET description = ?, confidence_score = ?, needs_review = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE object_name = ? AND field_name = ?
                """
                
                update_cursor = self.conn.execute(update_sql, (old_description, old_confidence, needs_review, object_name, field_name))
                if update_cursor.rowcount == 0:
                    return False
                
                # Record the revert in history
                revert_history_sql = """
                    INSERT INTO field_history (
                        metadata_id, object_name, field_name, 
                        field_description_old, field_description_new,
                        confidence_score_old, confidence_score_new,
                        change_type, change_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                self.conn.execute(revert_history_sql, (
                    current_record['id'], object_name, field_name,
                    current_record['description'], old_description,
                    current_record['confidence_score'], old_confidence,
                    'revert', f'Reverted to version from {history_dict["created_at"]}'
                ))
                
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error reverting field {object_name}.{field_name}: {e}")
            raise

# Example of how to use the service
if __name__ == '__main__':
    # This block is for demonstration and testing purposes.
    # It will run when the script is executed directly.
    logger.info("Running DatabaseService demonstration...")
    
    # Use a temporary database for the demo
    demo_db_path = "demo_metadata.db"
    
    try:
        with DatabaseService(db_path=demo_db_path) as db_service:
            # 1. Create the tables (including the new field_history table)
            db_service.create_metadata_table()
            logger.info("✅ Tables created successfully!")

            # 2. Define some mock records
            mock_records = [
                {
                    'object_name': 'Account',
                    'field_name': 'Name',
                    'field_label': 'Account Name',
                    'field_type': 'Text',
                    'is_custom': False,
                    'description': 'The official name of the account.',
                    'source': 'Salesforce',
                    'confidence_score': None,
                    'needs_review': False,
                    'raw_metadata': '{"type": "Name", "length": 255, "nillable": false, "unique": false}'
                },
                {
                    'object_name': 'Account',
                    'field_name': 'BillingState',
                    'field_label': 'Billing State/Province',
                    'field_type': 'Text',
                    'is_custom': False,
                    'description': 'The state or province of the billing address.',
                    'source': 'Salesforce',
                    'confidence_score': 9.5,
                    'needs_review': False,
                    'raw_metadata': '{"type": "string", "length": 80, "nillable": true, "inlineHelpText": "State or province for billing address"}'
                }
            ]

            # 3. Insert the mock records
            for record in mock_records:
                db_service.upsert_metadata_record(record)
            
            logger.info("✅ Mock records inserted successfully!")

            # 4. Test field history by updating a description
            logger.info("Testing field history functionality...")
            success = db_service.update_field_description(
                object_name='Account',
                field_name='BillingState',
                new_description='Updated: The state or province of the billing address (enhanced with AI analysis).',
                confidence_score=8.5
            )
            
            if success:
                logger.info("✅ Field description updated and history recorded!")
                
                # 5. Check the history
                history = db_service.get_field_history('Account', 'BillingState')
                logger.info(f"✅ Field history retrieved: {len(history)} records")
                for h in history:
                    logger.info(f"   - Change at {h['created_at']}: {h['change_type']}")
            
            logger.info("✅ Demo completed successfully!")

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise
