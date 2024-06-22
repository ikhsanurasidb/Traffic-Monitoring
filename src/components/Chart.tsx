"use client";

import { ResponsiveLine } from "@nivo/line";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface DataPoint {
  x: string | number;
  y: number;
}

interface LineData {
  id: string;
  color: string;
  data: DataPoint[];
}

interface MyResponsiveLineProps {
  data: LineData[];
}

const MyResponsiveLine = ({ data }: MyResponsiveLineProps) => (
  <ResponsiveLine
    data={data}
    margin={{ top: 50, right: 110, bottom: 50, left: 60 }}
    xScale={{ type: "point" }}
    yScale={{
      type: "linear",
      min: "auto",
      max: "auto",
      stacked: true,
      reverse: false,
    }}
    axisTop={null}
    axisRight={null}
    axisBottom={{
      tickSize: 5,
      tickPadding: 5,
      tickRotation: 0,
      legend: "transportation",
      legendOffset: 36,
      legendPosition: "middle",
      truncateTickAt: 0,
    }}
    axisLeft={{
      tickSize: 5,
      tickPadding: 5,
      tickRotation: 0,
      legend: "count",
      legendOffset: -40,
      legendPosition: "middle",
      truncateTickAt: 0,
    }}
    pointSize={10}
    pointColor={{ theme: "background" }}
    pointBorderWidth={2}
    pointBorderColor={{ from: "serieColor" }}
    pointLabel="data.yFormatted"
    pointLabelYOffset={-12}
    enableTouchCrosshair={true}
    useMesh={true}
    legends={[
      {
        anchor: "bottom-right",
        direction: "column",
        justify: false,
        translateX: 100,
        translateY: 0,
        itemsSpacing: 0,
        itemDirection: "left-to-right",
        itemWidth: 80,
        itemHeight: 20,
        itemOpacity: 0.75,
        symbolSize: 12,
        symbolShape: "circle",
        symbolBorderColor: "rgba(0, 0, 0, .5)",
        effects: [
          {
            on: "hover",
            style: {
              itemBackground: "rgba(0, 0, 0, .03)",
              itemOpacity: 1,
            },
          },
        ],
      },
    ]}
  />
);

const Chart = () => {
    const [data, setData] = useState<LineData[]>([]);

    const fetchData = async () => {
      const res = await fetch("/api/data");
      const json: LineData[] = await res.json();
      setData(json);
    };
  
    useEffect(() => {
      fetchData();
      const interval = setInterval(() => {
        fetchData();
      }, 10000); 
  
      return () => clearInterval(interval);
    }, []);
  
    const refreshChart = () => {
      fetchData();
    };

  return (
    <>
      <Button onClick={refreshChart}>Refresh 🔄</Button>
      <Card className="w-full h-[400px]">
        <MyResponsiveLine data={data} />
      </Card>
    </>
  );
};

export default Chart;
