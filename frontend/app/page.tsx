"use client";

import Link from "next/link";

interface RouteCard {
  title: string;
  path: string;
  badge: string;
  badgeColor: string;
  description: string;
  features: string[];
}

export default function HomePage() {
  const routes: RouteCard[] = [
    {
      title: "Admin Dashboard",
      path: "/admin",
      badge: "Internal",
      badgeColor: "bg-blue-100 text-blue-800",
      description: "Manage job postings, review incoming candidate pipelines, and make hiring decisions.",
      features: ["Create & edit career postings", "Review application records", "Update hiring status"],
    },
    {
      title: "User Portal",
      path: "/user",
      badge: "Public",
      badgeColor: "bg-emerald-100 text-emerald-800",
      description: "Candidate-facing workspace to browse available openings and submit applications.",
      features: ["Browse open positions", "Filter by department", "Submit job applications"],
    },
    {
      title: "Audit Stream",
      path: "/audit",
      badge: "System",
      badgeColor: "bg-purple-100 text-purple-800",
      description: "Real-time outbox event log viewer tracking system state changes across Kafka streams.",
      features: ["Live event stream monitoring", "Inspect JSON event payloads", "Verify publisher pipeline"],
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-10">
        
        {/* Uniform Design Header Section */}
        <header className="text-center max-w-2xl mx-auto space-y-3">
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-gray-200 text-gray-700 uppercase tracking-wider">
            Microservice Ecosystem
          </span>
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
            Recruitment Platform Gateway
          </h1>
          <p className="text-base text-gray-600">
            Select an operational route below to navigate between system modules and services.
          </p>
        </header>

        {/* Route Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {routes.map((route) => (
            <div
              key={route.path}
              className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col justify-between hover:shadow-md transition shadow-2xs group"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className={`px-2.5 py-0.5 text-xs font-bold rounded uppercase tracking-wide ${route.badgeColor}`}>
                    {route.badge}
                  </span>
                  <span className="text-xs font-mono text-gray-400 group-hover:text-blue-600 transition">
                    {route.path}
                  </span>
                </div>

                <div>
                  <h2 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition">
                    {route.title}
                  </h2>
                  <p className="mt-2 text-sm text-gray-600 leading-relaxed">
                    {route.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-gray-100 space-y-1.5">
                  {route.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center text-xs text-gray-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-300 mr-2" />
                      {feature}
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-4">
                <Link
                  href={route.path}
                  className="w-full flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-lg shadow-2xs transition"
                >
                  Launch App <span>→</span>
                </Link>
              </div>
            </div>
          ))}
        </div>

        {/* Footer Info Badge */}
        <footer className="text-center pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-400">
            Event-Driven Architecture • Django • Celery • Kafka • Next.js
          </p>
        </footer>

      </div>
    </div>
  );
}