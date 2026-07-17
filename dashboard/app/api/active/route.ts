import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { REPO_ROOT } from "@/lib/data";

export async function POST(request: Request) {
  let slug: unknown;
  try {
    ({ slug } = await request.json());
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  if (typeof slug !== "string" || !/^[a-z0-9-]+$/.test(slug)) {
    return NextResponse.json({ error: "Invalid slug" }, { status: 400 });
  }

  const profile = path.join(REPO_ROOT, "companies", slug, "profile.json");
  if (!fs.existsSync(profile)) {
    return NextResponse.json({ error: `No company brain found for "${slug}"` }, { status: 404 });
  }

  const activeFile = path.join(REPO_ROOT, "companies", "active-company.json");
  fs.writeFileSync(
    activeFile,
    JSON.stringify({ active: slug, switched_at: new Date().toISOString() }, null, 2) + "\n"
  );
  return NextResponse.json({ ok: true, active: slug });
}
