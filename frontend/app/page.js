"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

// Dynamically import MapView to ensure it only runs on the client side
const MapView = dynamic(() => import("../components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-screen">
      Loading map...
    </div>
  ),
});

export default function Home() {
  const [showMap, setShowMap] = useState(false);

  if (showMap) {
    return <MapView />;
  }

  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <h1 className="text-4xl font-bold text-center mb-8">GeoSpatial LLM</h1>

        <div className="flex flex-col gap-4 items-center">
          <button
            onClick={() => setShowMap(true)}
            className="rounded-full border border-solid border-transparent transition-colors flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white font-medium text-sm sm:text-base h-12 px-6"
          >
            🗺️ Open Map View
          </button>

          <p className="text-center text-gray-600 max-w-md">
            Click the button above to open the interactive map where you can
            draw regions of interest (ROI) and export them as GeoJSON.
          </p>
        </div>
      </main>
    </div>
  );
}
