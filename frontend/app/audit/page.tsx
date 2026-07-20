"use client";

import { useEffect, useState } from "react";

interface LogEntry {
  _id: string;
  log_type: string;
  sender: string;
  receiver: string;
  event_type: string;
  payload: Record<string, any>;
  occured_at: string;
}

interface ApiResponse {
  results: LogEntry[];
  total?: number; 
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 3;

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/audit/logs/?page=${currentPage}&size=${pageSize}`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch logs: ${response.statusText}`);
        }
        
        const data: ApiResponse = await response.json();
        setLogs(data.results || []);
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [currentPage]);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Audit Event Logs</h1>
            <p className="mt-2 text-sm text-gray-600">
              Paginated view of system events, payloads, and microservice communications.
            </p>
          </div>
          
          {/* Top Pagination Control */}
          <div className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage === 1 || loading}
              className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <span className="text-sm font-medium text-gray-700 px-2">
              Page {currentPage}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => prev + 1)}
              disabled={logs.length < pageSize || loading} // Disables next if we got fewer results than the page size
              className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Next
            </button>
          </div>
        </header>

        {/* Content States */}
        {loading ? (
          <div className="flex justify-center items-center py-24">
            <p className="text-lg font-medium text-gray-600 animate-pulse">Loading page {currentPage}...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg max-w-md mx-auto">
            <p className="font-bold">Error Loading Data</p>
            <p className="text-sm">{error}</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="bg-white text-center py-12 px-4 rounded-xl shadow-sm border border-gray-200">
            <p className="text-gray-500">No logs found on page {currentPage}.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {logs.map((log) => (
              <div 
                key={log._id} 
                className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden transition hover:shadow-md"
              >
                {/* Header info */}
                <div className="p-5 border-b border-gray-100 bg-gray-50/50 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center space-x-3">
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-100 text-blue-800 uppercase tracking-wider">
                      {log.log_type}
                    </span>
                    <h2 className="text-md font-semibold text-gray-800">
                      {log.event_type.replace(/_/g, " ")}
                    </h2>
                  </div>
                  <div className="text-xs text-gray-500 font-mono">
                    {new Date(log.occured_at).toLocaleString()}
                  </div>
                </div>

                {/* Microservice Communication Flow and JSON Display */}
                <div className="p-5 grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="space-y-4 lg:col-span-1">
                    <div>
                      <span className="block text-xs font-medium text-gray-400 uppercase tracking-wider">Log ID</span>
                      <span className="text-xs font-mono text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded break-all">
                        {log._id}
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2 text-sm">
                      <div className="flex-1 min-w-0">
                        <span className="block text-xs font-medium text-gray-400 uppercase tracking-wider">Sender</span>
                        <span className="font-medium text-gray-800 truncate block">{log.sender}</span>
                      </div>
                      <div className="text-gray-400 font-bold px-1">➔</div>
                      <div className="flex-1 min-w-0">
                        <span className="block text-xs font-medium text-gray-400 uppercase tracking-wider">Receiver</span>
                        <span className="font-medium text-gray-800 truncate block">{log.receiver}</span>
                      </div>
                    </div>
                  </div>

                  {/* Fully dynamic JSON payload box */}
                  <div className="lg:col-span-2">
                    <span className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                      Event Payload
                    </span>
                    <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto border border-gray-800 max-h-60">
                      <pre className="text-xs font-mono text-emerald-400 leading-relaxed">
                        {JSON.stringify(log.payload, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Bottom Pagination Control */}
            <div className="flex justify-center items-center space-x-4 pt-4">
              <button
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1 || loading}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
              >
                Previous Page
              </button>
              <span className="text-sm font-semibold text-gray-700">
                Page {currentPage}
              </span>
              <button
                onClick={() => setCurrentPage((prev) => prev + 1)}
                disabled={logs.length < pageSize || loading}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
              >
                Next Page
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}