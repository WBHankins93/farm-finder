"use client";

import type { FarmMapFeature, FarmSummary } from "../lib/discovery-contract";
import type { Farm } from "../lib/farms";
import FarmMap from "./farm-map";

type LegacyFarmMapProps = {
  visibleFarms: Farm[];
  selectedFarm: Farm | null;
  onSelect: (id: string | null) => void;
  onOpenProfile: (id: string) => void;
};

function summary(farm: Farm): FarmSummary {
  return { ...farm, distanceMiles: null };
}

export default function LegacyFarmMap({ visibleFarms, selectedFarm, onSelect, onOpenProfile }: LegacyFarmMapProps) {
  const features: FarmMapFeature[] = visibleFarms
    .filter((farm) => farm.geoPrecision !== "ungeocoded" && !(farm.latitude === 0 && farm.longitude === 0))
    .map((farm) => ({
      kind: "farm",
      id: farm.id,
      name: farm.name,
      category: farm.category,
      latitude: farm.latitude,
      longitude: farm.longitude,
      geoPrecision: farm.geoPrecision,
    }));

  return (
    <FarmMap
      features={features}
      selectedFarm={selectedFarm ? summary(selectedFarm) : null}
      hoveredFarm={null}
      userOrigin={null}
      scope={{ mode: "all", label: "all covered areas", origin: null, radiusMiles: null, bounds: null }}
      searchAreaAvailable={false}
      onSearchArea={() => undefined}
      onCameraChange={() => undefined}
      onSelect={(id) => onSelect(id || null)}
      onSelectCluster={() => undefined}
      onOpenProfile={onOpenProfile}
    />
  );
}
