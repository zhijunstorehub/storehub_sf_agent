import React, { useState, useMemo } from 'react';

// --- SVG ICONS (for a self-contained component) ---
const FlowIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
    <path d="M12 2L12 8"></path><path d="M12 16L12 22"></path><path d="M17 5L12 8L7 5"></path><path d="M17 19L12 16L7 19"></path>
  </svg>
);
const ApexClassIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-500">
    <polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>
  </svg>
);
const ApexTriggerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
  </svg>
);
const CustomObjectIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-500">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line>
  </svg>
);
const ValidationRuleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-yellow-500">
    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
  </svg>
);
const ChargebeeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-500">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
);
const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);
const RefreshCwIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>
);
const CheckCircleIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
);


// --- MOCK DATA (Now structured by data source) ---
const mockData = {
  Salesforce: {
    Flow: [
      {
        id: "flow_lead_inbound",
        name: "Lead_Inbound_2_0",
        analysis: { businessPurpose: "Automates the entire lifecycle for new inbound leads, from assignment to status updates.", confidenceScore: 8.5, risk: "Medium", complexity: "Complex" },
        dependencies: [{ name: "Lead", type: "CustomObject", direction: "references" }, { name: "Task", type: "CustomObject", direction: "creates" }],
        sourceCode: `<?xml version="1.0" encoding="UTF-8"?>\n<Flow ...>`,
      },
      {
        id: "flow_account_assign",
        name: "Account_Assign_BC_as_Owner",
        analysis: { businessPurpose: "Assigns the Account Owner to the 'BC Name' user when a new Account is created.", confidenceScore: 9.2, risk: "Low", complexity: "Simple" },
        dependencies: [{ name: "Account", type: "CustomObject", direction: "updates" }, { name: "User", type: "CustomObject", direction: "references" }],
        sourceCode: `<?xml version="1.0" encoding="UTF-8"?>\n<Flow ...>`,
      },
    ],
    ApexClass: [
      {
        id: "apex_quotation_controller",
        name: "QuotationController",
        analysis: { businessPurpose: "Manages server-side logic for quotations, including complex pricing calculations.", confidenceScore: 7.8, risk: "Medium", complexity: "Complex" },
        dependencies: [{ name: "Quote__c", type: "CustomObject", direction: "references" }, { name: "QuotationService", type: "ApexClass", direction: "calls" }],
        sourceCode: `public with sharing class QuotationController {\n    // ... Apex code ...\n}`,
      },
    ],
    CustomObject: [
      {
        id: "object_quote",
        name: "Quote__c",
        analysis: { businessPurpose: "Represents a formal offer for products or services to a customer.", confidenceScore: 9.0, risk: "High", complexity: "Moderate" },
        dependencies: [
          { name: "Opportunity", type: "CustomObject", direction: "related to" },
          { name: "RHX_Quote", type: "ApexTrigger", direction: "operates on" },
          { name: "Pro Tier Plan", type: "Chargebee Plan", direction: "creates subscription in" },
        ],
        sourceCode: `<CustomObject ...>\n    <label>Quote</label>\n</CustomObject>`,
      },
    ],
  },
  Chargebee: {
    "Subscription Plans": [
        {
            id: "chargebee_pro_plan",
            name: "Pro Tier Plan",
            analysis: { businessPurpose: "The primary subscription plan for professional users, offering advanced features.", confidenceScore: 9.9, risk: "High", complexity: "Simple" },
            dependencies: [{ name: "Quote__c", type: "Salesforce Object", direction: "created from" }, { name: "Stripe Gateway", type: "Payment Gateway", direction: "processed by" }],
            sourceCode: `{\n  "id": "pro-tier",\n  "name": "Pro Tier Plan",\n  "price": 9900,\n  "period_unit": "month"\n}`
        },
        {
            id: "chargebee_ent_plan",
            name: "Enterprise Plan",
            analysis: { businessPurpose: "Custom plan for enterprise clients with dedicated support and SLAs.", confidenceScore: 9.9, risk: "High", complexity: "Simple" },
            dependencies: [{ name: "Salesforce Contract", type: "Salesforce Object", direction: "created from" }],
            sourceCode: `{\n  "id": "enterprise-annual",\n  "name": "Enterprise Plan",\n  "price": 1200000,\n  "period_unit": "year"\n}`
        }
    ],
    "Coupons": [
        {
            id: "chargebee_promo25",
            name: "PROMO25",
            analysis: { businessPurpose: "Provides a 25% discount on the first 3 months for new Pro Tier customers.", confidenceScore: 9.5, risk: "Medium", complexity: "Simple" },
            dependencies: [{ name: "Pro Tier Plan", type: "Chargebee Plan", direction: "applies to" }],
            sourceCode: `{\n  "id": "PROMO25",\n  "discount_type": "percentage",\n  "discount_percentage": 25,\n  "duration_type": "limited_period",\n  "duration_month": 3\n}`
        }
    ]
  }
};

// --- UI COMPONENTS ---

const Header = ({ activeSource, setActiveSource }) => (
  <header className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
    <div className="flex items-center gap-3">
       <div className="bg-blue-600 p-2 rounded-lg">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
        </svg>
      </div>
      <h1 className="text-xl font-bold text-gray-800">Unified AI Colleague</h1>
    </div>
    <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
        <button onClick={() => setActiveSource('Salesforce')} className={`px-4 py-1.5 text-sm font-semibold rounded-md ${activeSource === 'Salesforce' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:bg-gray-200'}`}>Salesforce</button>
        <button onClick={() => setActiveSource('Chargebee')} className={`px-4 py-1.5 text-sm font-semibold rounded-md ${activeSource === 'Chargebee' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-600 hover:bg-gray-200'}`}>Chargebee</button>
    </div>
  </header>
);

const MetadataSidebar = ({ activeSource, onSelectComponent, selectedComponentId }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedTypes, setExpandedTypes] = useState(
    Object.keys(mockData[activeSource]).reduce((acc, type) => ({ ...acc, [type]: true }), {})
  );

  const currentSourceData = mockData[activeSource];

  const filteredData = useMemo(() => {
    if (!searchTerm) return currentSourceData;
    const lowercasedFilter = searchTerm.toLowerCase();
    return Object.entries(currentSourceData).reduce((acc, [type, components]) => {
      const filteredComponents = components.filter(c =>
        c.name.toLowerCase().includes(lowercasedFilter)
      );
      if (filteredComponents.length > 0) {
        acc[type] = filteredComponents;
      }
      return acc;
    }, {});
  }, [searchTerm, currentSourceData]);

  const toggleType = (type) => {
    setExpandedTypes(prev => ({ ...prev, [type]: !prev[type] }));
  };

  const getIconForType = (type) => {
    // Salesforce Icons
    if (activeSource === 'Salesforce') {
        switch (type) {
            case 'Flow': return <FlowIcon />;
            case 'ApexClass': return <ApexClassIcon />;
            case 'ApexTrigger': return <ApexTriggerIcon />;
            case 'CustomObject': return <CustomObjectIcon />;
            case 'ValidationRule': return <ValidationRuleIcon />;
        }
    }
    // Chargebee Icons
    if (activeSource === 'Chargebee') {
        return <ChargebeeIcon />;
    }
    return <div className="w-4 h-4" />;
  };

  return (
    <aside className="w-72 bg-gray-50 border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <input
            type="text"
            placeholder={`Search ${activeSource} components...`}
            className="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
            <SearchIcon />
          </div>
        </div>
      </div>
      <div className="flex-grow overflow-y-auto">
        <nav className="p-2">
          {Object.entries(filteredData).map(([type, components]) => (
            <div key={`${activeSource}-${type}`} className="mb-2">
              <button onClick={() => toggleType(type)} className="w-full flex items-center justify-between text-left p-2 rounded-md hover:bg-gray-200">
                <div className="flex items-center gap-2">
                  {getIconForType(type)}
                  <span className="font-semibold text-sm text-gray-700">{type}</span>
                </div>
                <span className="text-xs text-gray-500 bg-gray-200 rounded-full px-2 py-0.5">{components.length}</span>
              </button>
              {expandedTypes[type] && (
                <ul className="pl-4 mt-1 border-l-2 border-gray-200">
                  {components.map(component => (
                    <li key={component.id}>
                      <button
                        onClick={() => onSelectComponent(activeSource, type, component.id)}
                        className={`w-full text-left text-sm py-1.5 px-2 rounded-md truncate ${selectedComponentId === component.id ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        {component.name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
};

const AnalysisTab = ({ component }) => {
    const { businessPurpose, confidenceScore, risk, complexity } = component.analysis;
    const riskColor = risk === 'High' ? 'red' : risk === 'Medium' ? 'yellow' : 'green';
    const complexityColor = complexity === 'Complex' ? 'red' : complexity === 'Moderate' ? 'yellow' : 'green';
    const confidencePercentage = confidenceScore * 10;
  
    return (
      <div className="p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Business Purpose</h3>
          <p className="text-gray-700 leading-relaxed bg-gray-50 p-4 rounded-md border border-gray-200">{businessPurpose}</p>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">AI Confidence Score</h3>
          <div className="flex items-center gap-4">
            <div className="w-full bg-gray-200 rounded-full h-4"><div className={`bg-blue-500 h-4 rounded-full`} style={{ width: `${confidencePercentage}%` }}></div></div>
            <span className="text-lg font-bold text-blue-600">{confidenceScore.toFixed(1)}/10</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Risk Assessment</h3>
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-${riskColor}-100 text-${riskColor}-800`}><span className={`h-2 w-2 rounded-full bg-${riskColor}-500`}></span>{risk}</div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Complexity</h3>
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-${complexityColor}-100 text-${complexityColor}-800`}><span className={`h-2 w-2 rounded-full bg-${complexityColor}-500`}></span>{complexity}</div>
          </div>
        </div>
      </div>
    );
};

const DependenciesTab = ({ component }) => (
    <div className="p-6">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Component Dependencies</h3>
        <div className="border border-gray-200 rounded-md">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Component Name</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Relationship</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {component.dependencies.map((dep, index) => (
                        <tr key={index} className={dep.type.includes('Chargebee') || dep.type.includes('Salesforce') ? 'bg-indigo-50' : ''}>
                            <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-800">{dep.name}</td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">{dep.type}</td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{dep.direction}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

const SourceCodeTab = ({ component }) => (
    <div className="p-6 bg-gray-800 h-full overflow-y-auto">
        <pre className="text-sm text-gray-200 whitespace-pre-wrap">
            <code>{component.sourceCode}</code>
        </pre>
    </div>
);

const ComponentDetailView = ({ component }) => {
  const [activeTab, setActiveTab] = useState('analysis');

  if (!component) {
    return (
      <div className="flex-grow flex items-center justify-center bg-white"><div className="text-center">
        <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">Select a component</h3>
        <p className="mt-1 text-sm text-gray-500">Choose a component from the left to see its details.</p>
      </div></div>
    );
  }
  
  const isSalesforce = component.source === 'Salesforce';
  const tabs = [
    { id: 'analysis', label: 'Analysis' },
    { id: 'dependencies', label: 'Dependencies' },
    { id: 'sourceCode', label: isSalesforce ? 'Source Code' : 'JSON Configuration' },
  ];

  return (
    <main className="flex-grow bg-white flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-900">{component.name}</h2>
        <p className="text-sm text-gray-500">Source: {component.source} | Type: {component.type}</p>
      </div>
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex px-6" aria-label="Tabs">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm ${activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex-grow overflow-y-auto">
        {activeTab === 'analysis' && <AnalysisTab component={component} />}
        {activeTab === 'dependencies' && <DependenciesTab component={component} />}
        {activeTab === 'sourceCode' && <SourceCodeTab component={component} />}
      </div>
    </main>
  );
};

const ActionsPanel = ({ component }) => {
    const handleReanalyze = () => { if(component) alert(`Simulating re-analysis for: ${component.name}`); };
    const handleApprove = () => { if(component) alert(`Simulating approval for: ${component.name}`); };

    return (
        <aside className="w-80 bg-gray-50 border-l border-gray-200 p-6 space-y-8">
            <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Actions</h3>
                <button onClick={handleReanalyze} disabled={!component} className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed">
                    <RefreshCwIcon /> Re-analyze Component
                </button>
            </div>
            <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Curation</h3>
                <div className="bg-white p-4 rounded-md border border-gray-200 space-y-4">
                    <p className="text-sm text-gray-600">Review the AI's analysis. You can approve it to mark it as a trusted "golden record" for your team.</p>
                     <button onClick={handleApprove} disabled={!component} className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-300 disabled:cursor-not-allowed">
                        <CheckCircleIcon /> Approve Analysis
                    </button>
                </div>
            </div>
        </aside>
    );
};


// --- MAIN APP COMPONENT ---
export default function App() {
  const [activeSource, setActiveSource] = useState('Salesforce');
  const [selectedComponent, setSelectedComponent] = useState(null);

  const handleSelectComponent = (source, type, componentId) => {
    const component = mockData[source]?.[type]?.find(c => c.id === componentId);
    if (component) {
        setSelectedComponent({ ...component, source, type });
    }
  };
  
  const handleSetSource = (source) => {
      setActiveSource(source);
      setSelectedComponent(null); // Clear selection when changing source
  }

  return (
    <div className="h-screen w-full flex flex-col font-sans bg-gray-100 text-gray-900">
      <Header activeSource={activeSource} setActiveSource={handleSetSource} />
      <div className="flex flex-grow overflow-hidden">
        <MetadataSidebar activeSource={activeSource} onSelectComponent={handleSelectComponent} selectedComponentId={selectedComponent?.id} />
        <ComponentDetailView component={selectedComponent} />
        <ActionsPanel component={selectedComponent} />
      </div>
    </div>
  );
}
