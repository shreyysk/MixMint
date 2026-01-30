import RequireRole from "@/app/components/RequireRole";

export default function DJDashboard() {
  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold">DJ Dashboard</h1>
        <p>Manage your tracks, albums, and earnings.</p>
      </div>
    </RequireRole>
  );
}
