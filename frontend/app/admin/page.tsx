"use client";

import { useEffect, useState } from "react";

interface Job {
  id: number;
  title: string;
  department: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

interface Application {
  user_application_id: number;
  candidate_name: string;
  candidate_email: string;
  review_status: string;
  resume_url: null | string;
}

export default function AdminDashboard() {
  // Global View States
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingApps, setLoadingApps] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // Form Management States (Create/Edit Job)
  const [editingJob, setEditingJob] = useState<Partial<Job> | null>(null); // null means no active form, empty fields mean create
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);

  const BASE_URL = "http://localhost:8080/api/v1/admin/jobs";

  // --- Fetch Operations ---
  const fetchJobs = async () => {
    setLoadingJobs(true);
    try {
      const res = await fetch(`${BASE_URL}/`);
      if (!res.ok) throw new Error("Failed to pull job records.");
      const data = await res.json();
      setJobs(Array.isArray(data) ? data : data.results || []);
    } catch (err: any) {
      setGlobalError(err.message);
    } finally {
      setLoadingJobs(false);
    }
  };

  const fetchApplications = async (jobId: number) => {
    setLoadingApps(true);
    try {
      const res = await fetch(`${BASE_URL}/${jobId}/applications/`);
      if (!res.ok) throw new Error("Could not retrieve candidate lists.");
      const data = await res.json();
      console.log(data)
      setApplications(Array.isArray(data) ? data : data.results || []);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingApps(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      fetchApplications(selectedJobId);
    } else {
      setApplications([]);
    }
  }, [selectedJobId]);

  // --- Job Mutators (Create/Update/Delete) ---
  const openCreateForm = () => {
    setEditingJob({});
    setTitle("");
    setDepartment("");
    setDescription("");
    setIsActive(true);
  };

  const openEditForm = (job: Job) => {
    setEditingJob(job);
    setTitle(job.title);
    setDepartment(job.department);
    setDescription(job.description);
    setIsActive(job.is_active);
  };

  const saveJob = async (e: React.FormEvent) => {
    e.preventDefault();
    const isEditing = !!editingJob?.id;
    const url = isEditing ? `${BASE_URL}/${editingJob.id}/` : `${BASE_URL}/`;
    const method = isEditing ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, department, description, is_active: isActive }),
      });
      if (!res.ok) throw new Error("Failed to save job post.");
      
      setEditingJob(null);
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const deleteJob = async (id: number) => {
    if (!confirm("Are you sure you want to delete this job classification?")) return;
    try {
      const res = await fetch(`${BASE_URL}/${id}/`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to purge target system role.");
      if (selectedJobId === id) setSelectedJobId(null);
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // --- Application Status Mutator ---
  const updateAppStatus = async (appId: number, status: "hired" | "rejected") => {
    if (!selectedJobId) return;
    try {
      const res = await fetch(`${BASE_URL}/${selectedJobId}/applications/${appId}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_status: status }),
      });
      if (!res.ok) throw new Error("Application state adjustment rejected by backend.");
      
      // Refresh app column directly on complete
      fetchApplications(selectedJobId);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        
        {/* Uniform Design Header Section */}
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Internal Admin Center</h1>
            <p className="mt-2 text-sm text-gray-600">
              Manage core workspace careers, evaluate review pipelines, and hire application profiles.
            </p>
          </div>
          <button
            onClick={openCreateForm}
            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
          >
            + Create New Position
          </button>
        </header>

        {globalError && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-6 max-w-md">
            {globalError}
          </div>
        )}

        {/* Workspace Splitting Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* LEFT: Jobs Catalog View (7 Columns Wide) */}
          <div className="lg:col-span-7 space-y-4">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Active Openings Catalog</h2>
            
            {loadingJobs ? (
              <p className="text-gray-500 text-sm animate-pulse">Synchronizing database job rows...</p>
            ) : jobs.length === 0 ? (
              <div className="bg-white rounded-xl p-8 border border-gray-200 text-center text-gray-500 text-sm">No jobs added yet.</div>
            ) : (
              jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className={`p-5 rounded-xl border transition cursor-pointer flex flex-col sm:flex-row sm:items-start justify-between gap-4 ${
                    selectedJobId === job.id
                      ? "bg-blue-50/40 border-blue-300 shadow-sm"
                      : "bg-white border-gray-200 hover:shadow-md shadow-xs"
                  }`}
                >
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-0.5 text-xs font-semibold rounded-md bg-gray-100 text-gray-700 uppercase">
                        {job.department}
                      </span>
                      <span className={`w-2 h-2 rounded-full ${job.is_active ? "bg-emerald-500" : "bg-gray-300"}`} />
                    </div>
                    <h3 className="text-base font-bold text-gray-900 truncate">{job.title}</h3>
                    <p className="text-sm text-gray-600 line-clamp-2">{job.description}</p>
                  </div>

                  <div className="flex sm:flex-col items-center sm:items-end gap-2 shrink-0">
                    <button
                      onClick={(e) => { e.stopPropagation(); openEditForm(job); }}
                      className="px-2.5 py-1 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition"
                    >
                      Modify
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteJob(job.id); }}
                      className="px-2.5 py-1 text-xs font-semibold text-red-700 bg-red-50 hover:bg-red-100 rounded transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* RIGHT: Candidate Pipeline Panel (5 Columns Wide) */}
          <div className="lg:col-span-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
              Selected Role Applications
            </h2>

            {!selectedJobId ? (
              <div className="bg-white rounded-xl p-8 border border-gray-200 border-dashed text-center text-gray-400 text-sm">
                Select an open position from the left matrix layout to view candidate pipelines.
              </div>
            ) : loadingApps ? (
              <p className="text-gray-500 text-sm animate-pulse">Pulling applicant tracking matrices...</p>
            ) : applications.length === 0 ? (
              <div className="bg-white rounded-xl p-8 border border-gray-200 text-center text-gray-500 text-sm">
                No active applications received for this job index yet.
              </div>
            ) : (
              <div className="space-y-3">
                {applications.map((app) => (
                  <div key={app.user_application_id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
                    <div className="flex justify-between items-start mb-2 gap-2">
                      <div className="min-w-0">
                        <h4 className="font-bold text-gray-900 text-sm truncate">{app.candidate_name}</h4>
                        <p className="text-xs text-gray-500 truncate">{app.candidate_email}</p>
                      </div>
                      
                      {/* Interactive Evaluation Status Tags */}
                      <span className={`px-2 py-0.5 text-xs font-bold rounded uppercase tracking-wide shrink-0 ${
                        app.review_status === "hired" 
                          ? "bg-emerald-100 text-emerald-800" 
                          : app.review_status === "rejected"
                          ? "bg-red-100 text-red-800"
                          : "bg-amber-100 text-amber-800"
                      }`}>
                        {app.review_status}
                      </span>
                    </div>

                    {/* Operational Evaluation Buttons */}
                    <div className="mt-3 pt-3 border-t border-gray-100 flex gap-2 justify-end">
                    <div className="resume-container">
                      {app.resume_url ? (
                        <div className="resume-preview-wrapper">
                          {/* Inline PDF Preview */}
                          <iframe
                            src={`${app.resume_url}#toolbar=0`}
                            title="Resume Preview"
                            className="resume-iframe"
                            width="100%"
                            height="200px"
                          />
      
                          {/* Clickable link to open in new tab */}
                          <a 
                            href={app.resume_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="resume-preview-link text-blue-800 hover:underline"
                            style={{ display: 'block', marginTop: '10px' }}
                          >
                            Open Resume in New Tab
                          </a>
                        </div>
                      ) : (
                        <span className="no-resume-text">No resume available</span>
                      )}
                    </div>

                      <button
                        onClick={() => updateAppStatus(app.user_application_id, "rejected")}
                        disabled={app.review_status === "rejected"}
                        className="px-3 py-1 text-xs font-semibold rounded text-red-600 bg-white border border-gray-200 hover:bg-red-50 disabled:opacity-40 transition"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => updateAppStatus(app.user_application_id, "hired")}
                        disabled={app.review_status === "hired"}
                        className="px-3 py-1 text-xs font-semibold rounded text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 transition shadow-xs"
                      >
                        Hire Candidate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Modal Overlay: Job Management Creator/Editor Form */}
        {editingJob && (
          <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-5 py-4 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-bold text-gray-900">
                  {editingJob.id ? "Edit Position Details" : "Publish Career Role"}
                </h3>
                <button onClick={() => setEditingJob(null)} className="text-gray-400 hover:text-gray-600 font-bold">✕</button>
              </div>

              <form onSubmit={saveJob} className="p-5 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Position Title</label>
                  <input
                    type="text" required value={title} onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Lead Dev"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Department</label>
                  <input
                    type="text" required value={department} onChange={(e) => setDepartment(e.target.value)}
                    placeholder="e.g. software development"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Job Context / Description</label>
                  <textarea
                    rows={3} required value={description} onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide details about requirements..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox" id="isActiveCheck" checked={isActive} onChange={(e) => setIsActive(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500/20"
                  />
                  <label htmlFor="isActiveCheck" className="text-sm font-medium text-gray-700 select-none">
                    Mark position as active and visible
                  </label>
                </div>

                <div className="pt-2 flex space-x-3">
                  <button
                    type="button" onClick={() => setEditingJob(null)}
                    className="flex-1 px-4 py-2 text-sm font-semibold border rounded-lg hover:bg-gray-50 text-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-lg shadow-sm"
                  >
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}