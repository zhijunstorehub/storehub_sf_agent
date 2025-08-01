# 🚀 Supabase Migration Guide

This guide will help you migrate your Salesforce Metadata AI Colleague from SQLite to Supabase, unlocking powerful new capabilities like vector search, real-time updates, and better scalability.

## 🎯 Why Migrate to Supabase?

### **Immediate Benefits:**
- ✅ **No More Database Issues:** Eliminates SQLite concurrency and locking problems
- ✅ **Real-time Updates:** Live UI updates when data changes
- ✅ **Better Performance:** PostgreSQL handles complex queries better
- ✅ **Web Dashboard:** Manage your data through Supabase's web interface

### **Advanced Features You'll Gain:**
- 🔍 **Vector Search:** Semantic search through field descriptions using AI embeddings
- 📊 **Full-text Search:** Advanced PostgreSQL text search capabilities
- 🏢 **Multi-tenancy:** Support multiple Salesforce orgs easily
- 📈 **Better Analytics:** Complex aggregations and reporting
- 🔄 **Automatic Backups:** Built-in point-in-time recovery
- 🌐 **API Integration:** RESTful APIs auto-generated for all tables

## 📋 Migration Steps

### **Step 1: Create Supabase Project**

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Wait for the database to be ready (2-3 minutes)
4. Go to **Settings > API** and copy:
   - Project URL
   - `anon` public key
   - `service_role` secret key

### **Step 2: Set Up Database Schema**

1. In your Supabase dashboard, go to **SQL Editor**
2. Copy the contents of `supabase_migration.sql` 
3. Run the SQL script to create all tables and functions
4. Verify tables were created in **Table Editor**

### **Step 3: Configure Environment Variables**

Create a `.env` file (or update existing) with your Supabase credentials:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Keep existing variables for backwards compatibility
SALESFORCE_USERNAME=your-salesforce-username
SALESFORCE_PASSWORD=your-salesforce-password
SALESFORCE_SECURITY_TOKEN=your-security-token
OPENAI_API_KEY=your-openai-key  # For vector search
```

### **Step 4: Install Dependencies**

```bash
pip install -r requirements.txt
```

### **Step 5: Run Migration Script**

```bash
python migrate_to_supabase.py
```

The script will:
- ✅ Verify your Supabase connection
- ✅ Create organization record
- ✅ Migrate all objects and fields
- ✅ Preserve all existing data and history
- ✅ Verify migration success

### **Step 6: Update Backend Service**

Update your FastAPI server to use the new Supabase service:

```python
# In src/app/api/fastapi_server.py
from app.db.supabase_service import SupabaseService

# Replace the database service dependency
def get_db_service():
    return SupabaseService(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key,
        service_role_key=settings.supabase_service_key
    )
```

### **Step 7: Test Your Application**

1. Start the backend: `cd src && uvicorn app.api.fastapi_server:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Visit `http://localhost:3000` and test all functionality

## 🎉 New Capabilities After Migration

### **1. Real-time Field Updates**
Your UI can now subscribe to real-time changes:

```javascript
// Frontend real-time subscriptions
const subscription = supabase
  .channel('field-changes')
  .on('postgres_changes', 
    { event: 'UPDATE', schema: 'public', table: 'salesforce_fields' },
    payload => {
      // Auto-update UI when fields change
      updateFieldInUI(payload.new);
    }
  )
  .subscribe();
```

### **2. Semantic Search**
Search fields by meaning, not just text:

```javascript
// Search for fields related to "customer information"
const results = await supabaseService.searchFieldsSemantic(
  orgId, 
  "customer contact details", 
  10
);
```

### **3. Advanced Analytics**
Complex queries made easy:

```sql
-- Find all encrypted fields across objects
SELECT object_name, field_name, field_label
FROM salesforce_fields 
WHERE is_encrypted = true 
AND organization_id = 'your-org-id';

-- Get field completeness by object
SELECT 
  object_name,
  COUNT(*) as total_fields,
  COUNT(description) as fields_with_descriptions,
  ROUND(COUNT(description) * 100.0 / COUNT(*), 2) as completion_percentage
FROM salesforce_fields 
GROUP BY object_name
ORDER BY completion_percentage DESC;
```

### **4. Multi-Organization Support**
Easily manage multiple Salesforce orgs:

```python
# Create organizations for different Salesforce orgs
prod_org = supabase_service.create_organization(
    name="Production Org",
    salesforce_org_id="00D000000000001",
    is_sandbox=False
)

sandbox_org = supabase_service.create_organization(
    name="Sandbox Org", 
    salesforce_org_id="00D000000000002",
    is_sandbox=True
)
```

### **5. Enhanced Field History**
Comprehensive audit trail with version control:

```python
# Get detailed change history
history = supabase_service.get_field_history(org_id, "Account", "Name")

# Revert to any previous version
success = supabase_service.revert_field_to_version(
    org_id, "Account", "Name", history_id
)
```

## 🔧 Schema Overview

### **Core Tables:**
- `organizations` - Multi-tenant organization management
- `salesforce_objects` - Object metadata and properties  
- `salesforce_fields` - Enhanced field metadata with 25+ properties
- `field_history` - Complete change audit trail
- `analysis_jobs` - Track AI processing jobs
- `field_annotations` - User comments and corrections

### **Advanced Features:**
- **Vector Search:** `description_vector` column for semantic search
- **Full-text Search:** GIN indexes for fast text queries
- **Automatic History:** Triggers track all changes automatically
- **RLS Security:** Row-level security for multi-tenancy
- **Materialized Views:** Pre-computed summaries for fast dashboards

## 🛡️ Security & Performance

### **Row Level Security (RLS)**
Data is automatically isolated by organization:
```sql
-- Users can only see their organization's data
CREATE POLICY "Users can access their organization's data" 
ON salesforce_fields FOR ALL 
USING (organization_id = current_setting('app.current_org_id'));
```

### **Optimized Indexes**
- **Object queries:** Fast filtering by object_name
- **Field searches:** Full-text and vector similarity
- **History lookups:** Efficient change tracking
- **Analytics:** Optimized for aggregation queries

### **Automatic Backups**
- Point-in-time recovery up to 7 days
- Automated daily backups
- One-click restore functionality

## 🚨 Troubleshooting

### **Migration Issues**

**Problem:** Migration script fails with "table already exists"
```bash
# Solution: Reset the database schema
# In Supabase SQL Editor, run:
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
# Then re-run the migration.sql script
```

**Problem:** "Row Level Security" errors
```bash
# Solution: Disable RLS temporarily for testing
# In Supabase SQL Editor:
ALTER TABLE salesforce_fields DISABLE ROW LEVEL SECURITY;
```

**Problem:** Vector search not working
```bash
# Solution: Ensure pgvector extension is enabled
# In Supabase SQL Editor:
CREATE EXTENSION IF NOT EXISTS vector;
```

### **Backend Issues**

**Problem:** Import errors with SupabaseService
```bash
# Solution: Install dependencies
pip install supabase asyncpg sqlalchemy[postgresql]
```

**Problem:** Connection timeout errors
```bash
# Solution: Check your environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

## 📞 Support

If you encounter issues during migration:

1. **Check Logs:** Look at the migration script output for specific errors
2. **Verify Credentials:** Ensure all Supabase environment variables are correct
3. **Test Connection:** Use the Supabase dashboard to verify your database is accessible
4. **Check Schema:** Verify all tables were created properly in the Table Editor

## 🎯 Next Steps After Migration

1. **Enable Real-time Features:** Add subscriptions to your frontend
2. **Implement Semantic Search:** Set up OpenAI integration for vector embeddings
3. **Create Dashboards:** Use Supabase's analytics capabilities
4. **Set Up Backup Strategy:** Configure automated backups for your data
5. **Add More Organizations:** Import additional Salesforce orgs
6. **Implement User Authentication:** Add user management with Supabase Auth

---

🎉 **Congratulations!** You now have a modern, scalable metadata management platform with advanced capabilities that will grow with your needs. 