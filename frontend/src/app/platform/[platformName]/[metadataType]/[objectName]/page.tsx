'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { Search, ChevronDown, Sparkles, Database, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

type Field = {
  id: string;
  field_name: string;
  data_type: string;
  is_custom: boolean;
  description: string | null;
  ai_description: string | null;
  needs_review?: boolean;
};

type SortConfig = {
    key: keyof Field;
    direction: 'asc' | 'desc';
};

const ObjectFieldsPage = () => {
  const params = useParams();
  const objectName = params.objectName as string;
  const [fields, setFields] = useState<Field[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig[]>([
    { key: 'field_name', direction: 'asc' }
  ]);
  const [showNeedsReviewOnly, setShowNeedsReviewOnly] = useState(false);
  const [selectedDataTypes, setSelectedDataTypes] = useState<Set<string>>(new Set());
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const fetchFields = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:8000/api/metadata/objects/${objectName}`);
        if (!response.ok) {
          throw new Error('Failed to fetch fields');
        }
        const data = await response.json();
        setFields(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (objectName) {
      fetchFields();
    }
  }, [objectName]);

  const requestSort = (key: keyof Field) => {
    setSortConfig(prevConfig => {
      const newConfig = [...prevConfig];
      const existingSortIndex = newConfig.findIndex(sort => sort.key === key);

      if (existingSortIndex !== -1) {
        const existingSort = newConfig[existingSortIndex];
        if (existingSort.direction === 'asc') {
          existingSort.direction = 'desc';
        } else {
          newConfig.splice(existingSortIndex, 1);
        }
      } else {
        newConfig.push({ key, direction: 'asc' });
      }
      return newConfig;
    });
  };

    const getSortIndicator = (key: keyof Field) => {
        const sort = sortConfig.find(s => s.key === key);
        if (!sort) return null;
        return sort.direction === 'asc' ? '▲' : '▼';
    };

  const data = useMemo(() => {
    const filteredData = [...fields].filter(item => {
        const searchMatch = item.field_name.toLowerCase().includes(searchQuery.toLowerCase());
        const reviewMatch = !showNeedsReviewOnly || item.needs_review;
        const dataTypeMatch = selectedDataTypes.size === 0 || selectedDataTypes.has(item.data_type);
        return searchMatch && reviewMatch && dataTypeMatch;
    });

    if (sortConfig.length > 0) {
        filteredData.sort((a, b) => {
            for (const sort of sortConfig) {
                const { key, direction } = sort;
                const aValue = a[key];
                const bValue = b[key];

                if (aValue === undefined || aValue === null || bValue === undefined || bValue === null) {
                    return 0;
                }

                if (aValue < bValue) {
                    return direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return direction === 'asc' ? 1 : -1;
                }
            }
            return 0;
        });
    }

    return filteredData;
    }, [fields, searchQuery, sortConfig, showNeedsReviewOnly, selectedDataTypes]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedItems(new Set(data.map(item => item.id)));
    } else {
      setSelectedItems(new Set());
    }
  };

  const handleSelectItem = (id: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const availableDataTypes = useMemo(() => {
    const allTypes = fields.map(field => field.data_type);
    return [...new Set(allTypes)];
  }, [fields]);

  const handleDataTypeChange = (dataType: string) => {
    setSelectedDataTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dataType)) {
        newSet.delete(dataType);
      } else {
        newSet.add(dataType);
      }
      return newSet;
    });
  };

  return (
    <div className={`page-with-sidebar-container ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="filter-sidebar">
        <div className="filter-sidebar-header">
          <h3 className="filter-sidebar-title">Filters</h3>
          <button className="sidebar-toggle-btn" onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}>
            {isSidebarCollapsed ? <ChevronsRight size={20} /> : <ChevronsLeft size={20} />}
          </button>
        </div>
        <div className="filter-group">
          <h4 className="filter-group-title">Data Type</h4>
          {availableDataTypes.map(type => (
            <div key={type} className="filter-option">
              <input 
                type="checkbox" 
                id={`data-type-${type}`} 
                checked={selectedDataTypes.has(type)}
                onChange={() => handleDataTypeChange(type)}
              />
              <label htmlFor={`data-type-${type}`}>{type}</label>
            </div>
          ))}
        </div>
      </div>
      <div className="main-content-area">
        <div className="table-header">
            <h1 className="page-title">{objectName} Fields</h1>
            <div className="table-controls">
                <div className="search-box">
                    <Search size={16} className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search fields..."
                        className="search-input"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <button
                    className={`filter-toggle-btn ${showNeedsReviewOnly ? 'active' : ''}`}
                    onClick={() => setShowNeedsReviewOnly(!showNeedsReviewOnly)}
                >
                    Needs Review
                </button>
            </div>
        </div>

        {loading && <p>Loading...</p>}
        {error && <p className="error-message">{error}</p>}
        {!loading && !error && (
            <>
                <div className="data-table-container">
                    <table className="data-table">
                        <thead>
                        <tr>
                            <th><input type="checkbox" onChange={handleSelectAll} checked={selectedItems.size > 0 && selectedItems.size === data.length} /></th>
                            <th onClick={() => requestSort('field_name')}>
                                <div>Field Name <ChevronDown size={14} /></div>
                            </th>
                            <th onClick={() => requestSort('data_type')}>
                                <div>Data Type <ChevronDown size={14} /></div>
                            </th>
                            <th onClick={() => requestSort('is_custom')}>
                                <div>Is Custom <ChevronDown size={14} /></div>
                            </th>
                            <th>
                                <div>Description</div>
                            </th>
                        </tr>
                        </thead>
                        <tbody>
                        {data.map(item => (
                            <tr key={item.id} className={`${selectedItems.has(item.id) ? 'selected' : ''} ${item.needs_review ? 'needs-review' : ''}`}>
                                <td><input type="checkbox" checked={selectedItems.has(item.id)} onChange={() => handleSelectItem(item.id)} /></td>
                                <td>{item.field_name}</td>
                                <td>{item.data_type}</td>
                                <td>{item.is_custom ? 'Yes' : 'No'}</td>
                                <td>{item.ai_description || item.description || 'No description available'}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                </div>

                {selectedItems.size > 0 && (
                    <div className="contextual-action-bar">
                        <span className="selection-count">{selectedItems.size} item{selectedItems.size > 1 ? 's' : ''} selected</span>
                        <button className="action-button">
                            <Sparkles size={16} />
                            <span>Analyze Selected</span>
                        </button>
                    </div>
                )}
            </>
        )}
      </div>
    </div>
  );
};

export default ObjectFieldsPage; 