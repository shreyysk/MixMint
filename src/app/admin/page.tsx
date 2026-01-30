import RequireRole from "@/app/components/RequireRole";

export default function AdminPage() {
  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <p>Manage DJs, content, and platform settings.</p>
      </div>
    </RequireRole>
  );
}
