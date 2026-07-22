"use client";

import { useCallback, useEffect, useState } from "react";
import useWebsocket from "../hooks/useWebsocket";

interface Job {
    id: number;
    title: string;
    department: string;
    location: string;
    description: string;
}

interface NotificationItem {
    id: string;
    message: string;
    timestamp: string;
}

export default function UserJobsPage() {
    // Search and Filter States
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [department, setDepartment] = useState<string>("");
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Live Notification Queue State (Max 4 items)
    const [notifications, setNotifications] = useState<NotificationItem[]>([]);

    // Application Modal States
    const [selectedJob, setSelectedJob] = useState<Job | null>(null);
    const [email, setEmail] = useState<string>("");
    const [fullName, setFullName] = useState<string>("");
    const [skills, setSkills] = useState<string>("");
    const [submitting, setSubmitting] = useState<boolean>(false);
    const [submitMessage, setSubmitMessage] = useState<{
        type: "success" | "error";
        text: string;
    } | null>(null);

    // WebSocket Message Handler with FIFO Ring-Buffer Behavior
    const handleMessage = useCallback((data: any) => {
        console.log(data)
        if (data.type === "NOTIFICATION" && data.message) {
            const newNotice: NotificationItem = {
                id: `${Date.now()}-${Math.random().toString(36).substring(2, 5)}`,
                message: data.message,
                timestamp: new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                }),
            };

            setNotifications((prevNotices) => {
                // Prepend new item (newest first)
                const updated = [newNotice, ...prevNotices];
                // Cap strictly at the latest 4 items
                return updated.slice(0, 4);
            });
        }
    }, []);

    const { sendEvent } = useWebsocket(`ws/event/`, handleMessage);

    // Dismiss an individual notification manually
    const dismissNotification = (id: string) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
    };

    // Fetch jobs dynamically based on query and department changes
    useEffect(() => {
        const fetchJobs = async () => {
            setLoading(true);
            setError(null);
            try {
                // search/?q=${encodeURIComponent(searchQuery)}&department=${encodeURIComponent(department)}
                const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/user/jobs/search/?q=${encodeURIComponent(searchQuery)}&department=${encodeURIComponent(department)}`;
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error("Failed to load available positions");
                }
                const data = await response.json();
                // Fallback array mapping in case API structure directly mirrors the logs architecture
                setJobs(data.results || data || []);
            } catch (err: any) {
                setError(err.message || "An unexpected error occurred");
            } finally {
                setLoading(false);
            }
        };

        // Debounce search slightly to avoid hitting the backend on every keypress
        const delayDebounceFn = setTimeout(() => {
            fetchJobs();
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery, department]);

    // Handle Application Submit Form Actions
    const handleApply = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedJob) return;

        setSubmitting(true);
        setSubmitMessage(null);

        try {
            // 1. Grab the target file directly out of the DOM file element context
            const fileInput = document.getElementById(
                "resumeUpload",
            ) as HTMLInputElement;
            const file = fileInput?.files?.[0];

            if (!file) {
                throw new Error("Please upload your resume file to proceed.");
            }

            // 2. Initialize a native browser FormData instance container
            const formData = new FormData();
            formData.append("email", email);
            formData.append("full_name", fullName);
            formData.append("job_id", selectedJob.id.toString());
            formData.append("skills", skills); // Comma separated values string
            formData.append("resume", file); // Attaching the file binary safely

            // 3. Dispatch data. DO NOT set 'Content-Type' header here;
            // The browser automatically configures Multipart boundaries if FormData is specified.
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/user/apply/`,
                {
                    method: "POST",
                    body: formData,
                },
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.error || "Failed to submit application payload.",
                );
            }

            setSubmitMessage({
                type: "success",
                text: "Application submitted successfully!",
            });

            // Clear states
            setEmail("");
            setFullName("");
            setSkills("");
            if (fileInput) fileInput.value = ""; // Clear file selector UI box element
            setTimeout(() => setSelectedJob(null), 2000);
        } catch (err: any) {
            setSubmitMessage({
                type: "error",
                text: err.message || "Something went wrong.",
            });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">

            {/* Live Notifications Container - Top Right / Floating */}
{notifications.length > 0 && (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
        {notifications.map((notice) => (
            <div
                key={notice.id}
                className="pointer-events-auto bg-white/95 backdrop-blur-md border border-gray-200/90 p-3.5 rounded-xl shadow-md flex items-start justify-between gap-3 text-xs transition-all animate-in slide-in-from-top duration-200"
            >
                <div className="flex gap-2.5 items-start">
                    <span className="relative flex h-2 w-2 mt-1 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
                    </span>
                    <div>
                        <p className="font-semibold text-gray-800 leading-snug">
                            {notice.message}
                        </p>
                        <span className="text-[10px] text-gray-400 font-mono mt-1 block">
                            {notice.timestamp}
                        </span>
                    </div>
                </div>
                <button
                    onClick={() => dismissNotification(notice.id)}
                    className="text-gray-400 hover:text-gray-700 transition font-bold text-sm px-1 -mt-0.5 leading-none"
                    title="Dismiss notification"
                >
                    ✕
                </button>
            </div>
        ))}
    </div>
)}

            <div className="max-w-5xl mx-auto">
                {/* Header section matches log panel design */}
                <header className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                        Careers Portal
                    </h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Explore active openings across our departments and
                        launch your application instantly.
                    </p>
                </header>

                {/* Search & Filter Control Bar */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Search Keywords
                        </label>
                        <input
                            type="text"
                            placeholder="e.g. Engineer, Manager..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                            Filter Department
                        </label>
                        <select
                            value={department}
                            onChange={(e) => setDepartment(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
                        >
                            <option value="">All Departments</option>
                            <option value="software developement">
                                software developement
                            </option>
                            <option value="health care">health care</option>
                        </select>
                    </div>
                </div>

                {/* Content Status Rendering Blocks */}
                {loading ? (
                    <div className="flex justify-center items-center py-24">
                        <p className="text-lg font-medium text-gray-600 animate-pulse">
                            Scanning open roles...
                        </p>
                    </div>
                ) : error ? (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg max-w-md mx-auto text-center">
                        <p className="font-bold">Connection Error</p>
                        <p className="text-sm">{error}</p>
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="bg-white text-center py-12 px-4 rounded-xl shadow-sm border border-gray-200">
                        <p className="text-gray-500">
                            No career opportunities found matching your
                            criteria.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {jobs.map((job) => (
                            <div
                                key={job.id}
                                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition hover:shadow-md"
                            >
                                <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-md bg-blue-50 text-blue-700">
                                            {job.department}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-900">
                                        {job.title}
                                    </h3>
                                    <p className="text-sm text-gray-600 line-clamp-2 max-w-2xl">
                                        {job.description}
                                    </p>
                                </div>
                                <div className="shrink-0">
                                    <button
                                        onClick={() => {
                                            setSelectedJob(job);
                                            setSubmitMessage(null);
                                        }}
                                        className="w-full sm:w-auto px-5 py-2 text-sm font-semibold rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition active:scale-[0.98]"
                                    >
                                        Apply Now
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Application Form Overlay Modal */}
                {selectedJob && (
                    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
                        <div className="bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-md overflow-hidden transition-all animate-in fade-in zoom-in-95 duration-150">
                            <div className="px-5 py-4 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                                <div>
                                    <h3 className="font-bold text-gray-900">
                                        Apply Position
                                    </h3>
                                    <p className="text-xs text-gray-500 truncate max-w-70">
                                        {selectedJob.title}
                                    </p>
                                </div>
                                <button
                                    onClick={() => setSelectedJob(null)}
                                    className="text-gray-400 hover:text-gray-600 font-bold p-1 text-lg"
                                >
                                    ✕
                                </button>
                            </div>

                            <form
                                onSubmit={handleApply}
                                className="p-5 space-y-4"
                            >
                                {submitMessage && (
                                    <div
                                        className={`p-3 rounded-lg text-sm border font-medium ${
                                            submitMessage.type === "success"
                                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                                : "bg-red-50 text-red-800 border-red-200"
                                        }`}
                                    >
                                        {submitMessage.text}
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
                                        Full Name{" "}
                                        <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={fullName}
                                        onChange={(e) =>
                                            setFullName(e.target.value)
                                        }
                                        placeholder="Jane Doe"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
                                        Email Address{" "}
                                        <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) =>
                                            setEmail(e.target.value)
                                        }
                                        placeholder="jane.doe@example.com"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
                                        Skills{" "}
                                        <span className="text-red-500">*</span>
                                        {" "}
                                        <span className="text-gray-400 font-normal">
                                            (comma-separated)
                                        </span>
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={skills}
                                        onChange={(e) =>
                                            setSkills(e.target.value)
                                        }
                                        placeholder="React, TypeScript, Node.js"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-800 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
                                        Resume File{" "}
                                        <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="resumeUpload"
                                        type="file"
                                        required
                                        accept=".pdf"
                                        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 cursor-pointer border border-gray-300 rounded-lg p-1"
                                    />
                                </div>

                                <div className="pt-2 flex space-x-3">
                                    <button
                                        type="button"
                                        onClick={() => setSelectedJob(null)}
                                        className="flex-1 px-4 py-2 text-sm font-semibold rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        className="flex-1 px-4 py-2 text-sm font-semibold rounded-lg bg-gray-900 text-white hover:bg-gray-800 disabled:opacity-50 transition flex items-center justify-center shadow-sm"
                                    >
                                        {submitting
                                            ? "Submitting..."
                                            : "Submit Application"}
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
