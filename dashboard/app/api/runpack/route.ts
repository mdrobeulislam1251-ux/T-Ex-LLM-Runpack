import { NextResponse } from "next/server";
import { loadDashboardData } from "@/lib/data";

// Read-only summary of the whole runpack for external dashboards (see
// runpacks/grok-dashboard-builder.md). Exposes env var NAMES only — never
// secret values (lib/data.ts reads profile.json, which stores names only).
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(loadDashboardData());
}
