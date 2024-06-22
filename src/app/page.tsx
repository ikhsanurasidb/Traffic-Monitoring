
import Chart from "@/components/Chart";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <h1 className="text-5xl font-bold">Traffic Monitor Dashboard</h1>
      <Chart />
    </main>
  );
}
