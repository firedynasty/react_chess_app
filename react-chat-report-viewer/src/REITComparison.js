import React, { useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const REITComparison = () => {
  const comparisonData = [
    {
      metric: 'Property Types',
      PLD: 100,
      WELL: 100,
      description: 'PLD: Industrial/Logistics | WELL: Healthcare Facilities'
    },
    {
      metric: 'Geographic Presence',
      PLD: 19,
      WELL: 8,
      description: 'Number of countries with properties'
    },
    {
      metric: 'Tenant Diversity',
      PLD: 5800,
      WELL: 1400,
      description: 'Approximate number of customers'
    },
    {
      metric: 'Avg Lease Term',
      PLD: 5.5,
      WELL: 10.8,
      description: 'Average lease duration in years'
    }
  ];

  // Debug logging
  useEffect(() => {
    console.log('Rendering REITComparison component');
    console.log('Data:', comparisonData);
  }, []);

  return (
    <div className="w-full max-w-4xl mx-auto p-6 border rounded-lg shadow-lg bg-white">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Prologis (PLD) vs Welltower (WELL) Comparison</h2>
      </div>
      
      {/* Add explicit height and width to container */}
      <div style={{ width: '100%', height: '400px' }} className="mb-6">
        <ResponsiveContainer>
          <BarChart
            data={comparisonData}
            margin={{ top: 20, right: 30, left: 30, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="metric" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="PLD" fill="#1e40af" name="Prologis" />
            <Bar dataKey="WELL" fill="#047857" name="Welltower" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Add raw data display for debugging */}
      <div className="mb-6">
        <h3 className="font-bold mb-2">Raw Data (Debug):</h3>
        <pre className="bg-gray-100 p-4 rounded">
          {JSON.stringify(comparisonData, null, 2)}
        </pre>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 border rounded-lg">
          <h3 className="font-bold text-lg mb-2">Prologis (PLD)</h3>
          <ul className="list-disc pl-4 space-y-2">
            <li>Focus: Industrial and logistics real estate</li>
            <li>Global presence with significant scale</li>
            <li>Benefits from e-commerce growth</li>
            <li>Shorter lease terms but high renewal rates</li>
          </ul>
        </div>
        
        <div className="p-4 border rounded-lg">
          <h3 className="font-bold text-lg mb-2">Welltower (WELL)</h3>
          <ul className="list-disc pl-4 space-y-2">
            <li>Focus: Healthcare properties (senior housing, medical offices)</li>
            <li>Concentrated in US, UK, and Canada</li>
            <li>Benefits from aging demographics</li>
            <li>Longer lease terms with healthcare operators</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default REITComparison;