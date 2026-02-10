'use client';

import React from 'react';
import { Button } from '@/components/ui/Button';
import { Download } from 'lucide-react';

interface ExportButtonProps {
    data: any[];
    filename: string;
    className?: string;
}

export function ExportButton({ data, filename, className }: ExportButtonProps) {
    const handleExport = () => {
        if (!data || data.length === 0) return;

        // 1. Get headers
        const headers = Object.keys(data[0]);

        // 2. Format CSV content
        const csvRows = [
            headers.join(','), // Header row
            ...data.map(row =>
                headers.map(header => {
                    const value = row[header];
                    // Handle commas, quotes, and objects
                    const cell = typeof value === 'object' ? JSON.stringify(value) : String(value);
                    return `"${cell.replace(/"/g, '""')}"`;
                }).join(',')
            )
        ];

        const csvString = csvRows.join('\n');
        const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);

        // 3. Trigger download
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <Button
            onClick={handleExport}
            className={`bg-zinc-900 border border-zinc-800 text-zinc-300 gap-2 rounded-xl hover:bg-zinc-800 transition-all ${className}`}
        >
            <Download size={16} />
            Export CSV
        </Button>
    );
}
