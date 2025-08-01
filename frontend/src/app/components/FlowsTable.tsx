'use client';

import React from 'react';
import { Table, TableHeader, TableColumn, TableBody, TableRow, TableCell } from "@heroui/react";

interface Flow {
  id: string;
  flow_name: string;
  description: string;
  process_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface FlowsTableProps {
  flows: Flow[];
}

export default function FlowsTable({ flows }: FlowsTableProps) {
  return (
    <Table aria-label="Flows table">
      <TableHeader>
        <TableColumn>Flow Name</TableColumn>
        <TableColumn>Description</TableColumn>
        <TableColumn>Process Type</TableColumn>
        <TableColumn>Status</TableColumn>
      </TableHeader>
      <TableBody>
        {flows.map((flow) => (
          <TableRow key={flow.id}>
            <TableCell>{flow.flow_name}</TableCell>
            <TableCell>{flow.description}</TableCell>
            <TableCell>{flow.process_type}</TableCell>
            <TableCell>{flow.status}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
} 