import { NextRequest, NextResponse } from "next/server";
import { openDb } from "@/lib/db";

type DataItem = {
  location: string;
  object_type: string;
  count: number;
};

type FormattedData = {
  id: string;
  color: string;
  data: { x: string; y: number }[];
};

export async function GET(req: NextRequest) {
  const db = openDb();
  const query = `
      SELECT location, object_type, SUM(in_count + out_count) as count 
      FROM traffic_counts 
      GROUP BY location, object_type
    `;
  const result: DataItem[] = db.prepare(query).all() as DataItem[];

  const formattedData: FormattedData[] = result.reduce((acc, row) => {
    let location = acc.find((loc) => loc.id === row.location);
    if (!location) {
      location = { id: row.location, color: "hsl(65, 70%, 50%)", data: [] };
      acc.push(location);
    }
    location.data.push({ x: row.object_type, y: row.count });
    return acc;
  }, [] as FormattedData[]);

  return NextResponse.json(formattedData);
}
