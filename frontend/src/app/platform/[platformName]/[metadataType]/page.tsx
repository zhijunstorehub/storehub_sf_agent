'use client';

import React, { useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Search, ChevronDown, Sparkles } from 'lucide-react';

type DataObject = {
  id: string;
  name: string;
  fields: number;
  custom_fields: number;
  last_analyzed: string;
  needs_review?: boolean;
};

type SortConfig = {
  key: keyof DataObject;
  direction: 'asc' | 'desc';
};

// Mock Data
const mockData: { [key: string]: DataObject[] } = {
  objects: [
    { id: '1', name: 'Account', fields: 50, custom_fields: 10, last_analyzed: '2024-07-29', needs_review: true },
    { id: '2', name: 'Contact', fields: 40, custom_fields: 5, last_analyzed: '2024-07-28' },
    { id: '3', name: 'Opportunity', fields: 60, custom_fields: 15, last_analyzed: '2024-07-29', needs_review: true },
    { id: '4', name: 'Lead', fields: 30, custom_fields: 8, last_analyzed: '2024-07-27' },
  ],
  flows: [
    { id: '5', name: 'New Lead Flow', fields: 0, custom_fields: 0, last_analyzed: '2024-07-29' },
    { id: '6', name: 'Opportunity Close Flow', fields: 0, custom_fields: 0, last_analyzed: '2024-07-28' },
  ]
};

const DataTablePage = () => {
  const [showNeedsReviewOnly, setShowNeedsReviewOnly] = useState(false);
  const router = useRouter();
  const params = useParams();
  const metadataType = params.metadataType as keyof typeof mockData;
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig[]>([
    { key: 'name', direction: 'asc' }
  ]);
  const [columnWidths, setColumnWidths] = useState({
    name: 250,
    fields: 150,
    custom_fields: 150,
    last_analyzed: 200,
  });

  const data = useMemo(() => {
    const tableData = [...(mockData[metadataType as keyof typeof mockData] || [])];

    const filteredData = tableData.filter(item => {
      const searchMatch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
      const reviewMatch = !showNeedsReviewOnly || item.needs_review;
      return searchMatch && reviewMatch;
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
  }, [metadataType, searchQuery, sortConfig, showNeedsReviewOnly]);

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

  const handleRowClick = (itemName: string) => () => {
    router.push(`/platform/${params.platformName}/${metadataType}/${itemName}`);
  };

  const requestSort = (key: keyof DataObject) => {
    setSortConfig(prevConfig => {
      const newConfig = [...prevConfig];
      const existingSortIndex = newConfig.findIndex(sort => sort.key === key);

      if (existingSortIndex !== -1) {
        const existingSort = newConfig[existingSortIndex];
        if (existingSort.direction === 'asc') {
          existingSort.direction = 'desc';
        } else {
          // If descending, remove it from the sort
          newConfig.splice(existingSortIndex, 1);
        }
      } else {
        // If not sorted, add it as ascending
        newConfig.push({ key, direction: 'asc' });
      }
      return newConfig;
    });
  };

  const getSortIndicator = (key: keyof DataObject) => {
    const sort = sortConfig.find(s => s.key === key);
    if (!sort) return null;
    return sort.direction === 'asc' ? '▲' : '▼';
  };

  const startResizing = (
    e: React.MouseEvent<HTMLDivElement>,
    column: keyof typeof columnWidths
  ) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = columnWidths[column];

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = startWidth + (e.clientX - startX);
      if (newWidth > 100) { // Minimum width
        setColumnWidths(prev => ({ ...prev, [column]: newWidth }));
      }
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div className="page-container">
      <div className="table-header">
        <h1 className="page-title">{String(metadataType).charAt(0).toUpperCase() + String(metadataType).slice(1)}</h1>
        <div className="table-controls">
          <div className="search-box">
            <Search size={16} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search..." 
              className="search-input" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button 
            onClick={() => setShowNeedsReviewOnly(!showNeedsReviewOnly)}
            className={`filter-toggle-btn ${showNeedsReviewOnly ? 'active' : ''}`}
          >
            Needs Review
          </button>
        </div>
      </div>

      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 50 }}><input type="checkbox" onChange={handleSelectAll} /></th>
              <th style={{ width: columnWidths.name }} onClick={() => requestSort('name')}>
                <div>
                  Name {getSortIndicator('name')}
                </div>
                <div className="resize-handle" onMouseDown={(e) => startResizing(e, 'name')} />
              </th>
              <th style={{ width: columnWidths.fields }} onClick={() => requestSort('fields')}>
                <div>
                  Fields {getSortIndicator('fields')}
                </div>
                <div className="resize-handle" onMouseDown={(e) => startResizing(e, 'fields')} />
              </th>
              <th style={{ width: columnWidths.custom_fields }} onClick={() => requestSort('custom_fields')}>
                <div>
                  Custom Fields {getSortIndicator('custom_fields')}
                </div>
                <div className="resize-handle" onMouseDown={(e) => startResizing(e, 'custom_fields')} />
              </th>
              <th style={{ width: columnWidths.last_analyzed }} onClick={() => requestSort('last_analyzed')}>
                <div>
                  Last Analyzed {getSortIndicator('last_analyzed')}
                </div>
                <div className="resize-handle" onMouseDown={(e) => startResizing(e, 'last_analyzed')} />
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map(item => (
              <tr 
                key={item.id} 
                className={`${selectedItems.has(item.id) ? 'selected' : ''} ${item.needs_review ? 'needs-review' : ''}`}
                onClick={handleRowClick(item.name)}
                style={{ cursor: 'pointer' }}
              >
                <td><input 
                  type="checkbox" 
                  checked={selectedItems.has(item.id)} 
                  onClick={(e) => e.stopPropagation()} 
                  onChange={() => handleSelectItem(item.id)} 
                /></td>
                <td>{item.name}</td>
                <td>{item.fields}</td>
                <td>{item.custom_fields}</td>
                <td>{item.last_analyzed}</td>
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
    </div>
  );
};

export default DataTablePage; 