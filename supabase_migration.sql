-- Supabase Migration for Salesforce Metadata AI Colleague
-- This creates a comprehensive schema for managing Salesforce metadata with semantic search capabilities

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create enum types for better data integrity
CREATE TYPE field_source AS ENUM ('salesforce_api', 'ai_generated', 'manual', 'documentation');
CREATE TYPE change_type AS ENUM ('description', 'confidence', 'both', 'revert', 'initial');
CREATE TYPE analysis_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'needs_review');

-- Main organizations table (for multi-tenancy)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    salesforce_org_id TEXT UNIQUE,
    domain TEXT,
    api_version TEXT DEFAULT '59.0',
    is_sandbox BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Salesforce objects table
CREATE TABLE salesforce_objects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    object_name TEXT NOT NULL,
    object_label TEXT,
    object_type TEXT, -- 'standard', 'custom', 'external'
    is_custom BOOLEAN DEFAULT false,
    description TEXT,
    key_prefix TEXT,
    record_count BIGINT,
    api_accessible BOOLEAN DEFAULT true,
    queryable BOOLEAN DEFAULT true,
    searchable BOOLEAN DEFAULT true,
    raw_metadata JSONB,
    last_analyzed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, object_name)
);

-- Enhanced salesforce fields table
CREATE TABLE salesforce_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    object_id UUID REFERENCES salesforce_objects(id) ON DELETE CASCADE,
    object_name TEXT NOT NULL, -- Denormalized for easier queries
    field_name TEXT NOT NULL,
    field_label TEXT,
    field_type TEXT,
    data_type TEXT, -- Computed friendly type
    is_custom BOOLEAN DEFAULT false,
    
    -- Core description and AI analysis
    description TEXT,
    ai_description TEXT, -- AI-generated description
    source field_source DEFAULT 'salesforce_api',
    confidence_score DECIMAL(3,1) CHECK (confidence_score >= 0 AND confidence_score <= 10),
    needs_review BOOLEAN DEFAULT false,
    analysis_status analysis_status DEFAULT 'pending',
    
    -- Enhanced metadata from Salesforce API
    help_text TEXT,
    is_required BOOLEAN DEFAULT false,
    is_unique BOOLEAN DEFAULT false,
    is_encrypted BOOLEAN DEFAULT false,
    is_external_id BOOLEAN DEFAULT false,
    is_formula BOOLEAN DEFAULT false,
    is_auto_number BOOLEAN DEFAULT false,
    
    -- Field constraints and properties
    field_length INTEGER,
    precision_digits INTEGER,
    scale_digits INTEGER,
    default_value TEXT,
    
    -- Relationship information
    relationship_name TEXT,
    reference_to TEXT[], -- Array of object names
    cascade_delete BOOLEAN DEFAULT false,
    restricted_delete BOOLEAN DEFAULT false,
    
    -- Picklist information
    picklist_values JSONB,
    controlling_field TEXT,
    dependent_picklist BOOLEAN DEFAULT false,
    restricted_picklist BOOLEAN DEFAULT false,
    
    -- Query and display properties
    filterable BOOLEAN DEFAULT true,
    sortable BOOLEAN DEFAULT true,
    groupable BOOLEAN DEFAULT true,
    aggregatable BOOLEAN DEFAULT false,
    
    -- Full raw metadata from Salesforce
    raw_metadata JSONB,
    
    -- Semantic search vector (for AI descriptions)
    description_vector vector(1536), -- OpenAI embedding dimension
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_analyzed_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(organization_id, object_name, field_name)
);

-- Field change history table with enhanced tracking
CREATE TABLE field_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID REFERENCES salesforce_fields(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    object_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    
    -- What changed
    change_type change_type NOT NULL,
    
    -- Old and new values
    description_old TEXT,
    description_new TEXT,
    ai_description_old TEXT,
    ai_description_new TEXT,
    confidence_score_old DECIMAL(3,1),
    confidence_score_new DECIMAL(3,1),
    analysis_status_old analysis_status,
    analysis_status_new analysis_status,
    
    -- Change metadata
    changed_by TEXT DEFAULT 'system',
    change_reason TEXT,
    user_feedback TEXT, -- User comments on the change
    
    -- Version tracking
    version_number INTEGER DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis jobs table for tracking AI processing
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL, -- 'field_analysis', 'batch_analysis', 'semantic_search_index'
    status analysis_status DEFAULT 'pending',
    
    -- Job configuration
    config JSONB, -- Job-specific configuration
    target_objects TEXT[], -- Objects to process
    target_fields JSONB, -- Specific fields to process
    
    -- Progress tracking
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    
    -- Results and errors
    results JSONB,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User feedback and annotations
CREATE TABLE field_annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID REFERENCES salesforce_fields(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    annotation_type TEXT NOT NULL, -- 'correction', 'enhancement', 'business_context'
    content TEXT NOT NULL,
    author TEXT,
    is_approved BOOLEAN DEFAULT false,
    approved_by TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_salesforce_fields_object ON salesforce_fields(organization_id, object_name);
CREATE INDEX idx_salesforce_fields_needs_review ON salesforce_fields(organization_id, needs_review) WHERE needs_review = true;
CREATE INDEX idx_salesforce_fields_confidence ON salesforce_fields(organization_id, confidence_score);
CREATE INDEX idx_salesforce_fields_analysis_status ON salesforce_fields(organization_id, analysis_status);
CREATE INDEX idx_salesforce_fields_is_custom ON salesforce_fields(organization_id, is_custom);
CREATE INDEX idx_salesforce_fields_field_type ON salesforce_fields(organization_id, field_type);

-- Full-text search indexes
CREATE INDEX idx_salesforce_fields_description_fts ON salesforce_fields USING gin(to_tsvector('english', COALESCE(description, '')));
CREATE INDEX idx_salesforce_fields_field_name_fts ON salesforce_fields USING gin(to_tsvector('english', field_name || ' ' || COALESCE(field_label, '')));

-- Vector similarity search index (for semantic search)
CREATE INDEX idx_salesforce_fields_description_vector ON salesforce_fields USING ivfflat (description_vector vector_cosine_ops) WITH (lists = 100);

-- History indexes
CREATE INDEX idx_field_history_field ON field_history(field_id, created_at DESC);
CREATE INDEX idx_field_history_changes ON field_history(organization_id, object_name, field_name, created_at DESC);

-- RLS (Row Level Security) policies for multi-tenancy
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE salesforce_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE salesforce_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_annotations ENABLE ROW LEVEL SECURITY;

-- Create policies (you'll need to customize these based on your auth setup)
CREATE POLICY "Users can access their organization's data" ON salesforce_fields
    FOR ALL USING (organization_id = (SELECT id FROM organizations WHERE salesforce_org_id = current_setting('app.current_org_id', true)));

-- Automatic updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_salesforce_objects_updated_at BEFORE UPDATE ON salesforce_objects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_salesforce_fields_updated_at BEFORE UPDATE ON salesforce_fields
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_field_annotations_updated_at BEFORE UPDATE ON field_annotations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create field history records
CREATE OR REPLACE FUNCTION track_field_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Only track if there are actual changes to tracked fields
    IF OLD.description IS DISTINCT FROM NEW.description OR
       OLD.ai_description IS DISTINCT FROM NEW.ai_description OR
       OLD.confidence_score IS DISTINCT FROM NEW.confidence_score OR
       OLD.analysis_status IS DISTINCT FROM NEW.analysis_status THEN
        
        INSERT INTO field_history (
            field_id, organization_id, object_name, field_name,
            change_type,
            description_old, description_new,
            ai_description_old, ai_description_new,
            confidence_score_old, confidence_score_new,
            analysis_status_old, analysis_status_new,
            changed_by, change_reason,
            version_number
        ) VALUES (
            NEW.id, NEW.organization_id, NEW.object_name, NEW.field_name,
            CASE 
                WHEN OLD.description IS DISTINCT FROM NEW.description AND OLD.confidence_score IS DISTINCT FROM NEW.confidence_score THEN 'both'
                WHEN OLD.description IS DISTINCT FROM NEW.description THEN 'description'
                WHEN OLD.confidence_score IS DISTINCT FROM NEW.confidence_score THEN 'confidence'
                WHEN OLD.ai_description IS DISTINCT FROM NEW.ai_description AND OLD.analysis_status IS DISTINCT FROM NEW.analysis_status THEN 'both'
                WHEN OLD.ai_description IS DISTINCT FROM NEW.ai_description THEN 'description'
                ELSE 'initial'
            END,
            OLD.description, NEW.description,
            OLD.ai_description, NEW.ai_description,
            OLD.confidence_score, NEW.confidence_score,
            OLD.analysis_status, NEW.analysis_status,
            COALESCE(current_setting('app.current_user', true), 'system'),
            COALESCE(current_setting('app.change_reason', true), 'Field updated'),
            COALESCE((SELECT MAX(version_number) + 1 FROM field_history WHERE field_id = NEW.id), 1)
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_salesforce_field_changes
    AFTER UPDATE ON salesforce_fields
    FOR EACH ROW
    EXECUTE FUNCTION track_field_changes();

-- Views for common queries
CREATE VIEW field_summary AS
SELECT 
    sf.organization_id,
    sf.object_name,
    COUNT(*) as total_fields,
    COUNT(*) FILTER (WHERE sf.is_custom = true) as custom_fields,
    COUNT(*) FILTER (WHERE sf.needs_review = true) as fields_needing_review,
    AVG(sf.confidence_score) as avg_confidence_score,
    COUNT(*) FILTER (WHERE sf.description IS NOT NULL) as fields_with_description,
    COUNT(*) FILTER (WHERE sf.analysis_status = 'completed') as analyzed_fields
FROM salesforce_fields sf
GROUP BY sf.organization_id, sf.object_name;

-- Insert default organization (you can modify this)
INSERT INTO organizations (name, salesforce_org_id, domain) 
VALUES ('Default Organization', 'default', 'localhost') 
ON CONFLICT (salesforce_org_id) DO NOTHING; 