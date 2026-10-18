import { loadDashboardData } from "@/lib/data";
import { CommandDeck } from "@/components/command-deck";

export const dynamic = "force-dynamic";

export default function Page() {
  const data = loadDashboardData();
  return <CommandDeck data={data} />;
}
