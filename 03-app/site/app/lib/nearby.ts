"use client";

import { useEffect, useState } from "react";
import type { Farm } from "./farms";

/**
 * Data-access seam for the farm directory.
 *
 * Today it fetches the full published feed (`/farms.json`) once and answers
 * proximity queries client-side. The interface — `nearestFarms(origin, farms)`
 * — is intentionally the shape a spatial API / D1 / Postgres backend would
 * expose (`GET /farms/nearby?lat=&lng=`), so the backend can be swapped in
 * later without touching the UI. That swap is the next optimization: the feed
 * is ~45 MB, so nearby-only loading is the path to a fast first paint.
 */

export type LatLng = { lat: number; lng: number };

// Default map center when the visitor hasn't shared a location yet — the
// original launch market (South Louisiana).
export const DEFAULT_ORIGIN: LatLng = { lat: 30.15, lng: -91.35 };

const EARTH_KM = 6371;
const toRad = (d: number) => (d * Math.PI) / 180;

/** Great-circle distance in kilometers. */
export function haversineKm(a: LatLng, b: LatLng): number {
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.min(1, Math.sqrt(s)));
}

/** Distance a mappable farm sits from an origin; ungeocoded farms sort last. */
export function farmDistanceKm(origin: LatLng, farm: Farm): number {
  if (farm.geoPrecision === "ungeocoded" || (!farm.latitude && !farm.longitude)) {
    return Number.POSITIVE_INFINITY;
  }
  return haversineKm(origin, { lat: farm.latitude, lng: farm.longitude });
}

/** Farms nearest an origin, closest first. Pure and cheap over the full set. */
export function nearestFarms(origin: LatLng, farms: Farm[]): Farm[] {
  return [...farms].sort((a, b) => farmDistanceKm(origin, a) - farmDistanceKm(origin, b));
}

export type FarmsState = {
  farms: Farm[];
  loading: boolean;
  error: string;
};

/** Load the published feed once. Empty + loading until it resolves. */
export function useFarms(): FarmsState {
  const [state, setState] = useState<FarmsState>({ farms: [], loading: true, error: "" });

  useEffect(() => {
    let alive = true;
    fetch("/farms.json")
      .then((res) => {
        if (!res.ok) throw new Error(`feed ${res.status}`);
        return res.json();
      })
      .then((data: Farm[]) => {
        if (alive) setState({ farms: data, loading: false, error: "" });
      })
      .catch(() => {
        if (alive) setState({ farms: [], loading: false, error: "We couldn't load the farm directory." });
      });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}

/** Ask the browser for the visitor's location. Resolves null if unavailable. */
export function requestLocation(): Promise<LatLng | null> {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lng: coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  });
}
