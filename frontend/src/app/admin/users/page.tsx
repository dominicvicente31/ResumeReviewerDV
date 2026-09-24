"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";

export default function AdminUsersPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.push("/dashboard");
  }, [loading, user, router]);

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.listUsers().then((r) => r.data),
    enabled: user?.role === "admin",
  });

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"user" | "admin">("user");
  const [formError, setFormError] = useState("");

  const createUser = useMutation({
    mutationFn: () => adminApi.createUser(email, password, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setShowForm(false);
      setEmail("");
      setPassword("");
      setRole("user");
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(msg ?? "Failed to create user.");
    },
  });

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Users</h1>
          <Button onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Add User"}
          </Button>
        </div>

        {showForm && (
          <div className="rounded-lg border p-4 space-y-4">
            <h2 className="font-semibold">New User</h2>
            {formError && <Alert variant="destructive">{formError}</Alert>}
            <div className="space-y-1">
              <Label>Email</Label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Role</Label>
              <div className="flex gap-4">
                {(["user", "admin"] as const).map((r) => (
                  <label key={r} className="flex items-center gap-1.5 cursor-pointer text-sm">
                    <input type="radio" checked={role === r} onChange={() => setRole(r)} />
                    {r}
                  </label>
                ))}
              </div>
            </div>
            <Button
              onClick={() => { setFormError(""); createUser.mutate(); }}
              disabled={createUser.isPending || !email || !password}
            >
              {createUser.isPending ? "Creating…" : "Create User"}
            </Button>
          </div>
        )}

        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && users?.length === 0 && (
          <p className="text-muted-foreground text-sm">No users found.</p>
        )}

        {!isLoading && users && users.length > 0 && (
          <div className="rounded-lg border divide-y">
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{u.email}</span>
                    {u.id === user.id && (
                      <span className="text-xs text-muted-foreground">(you)</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Joined {new Date(u.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {!u.is_verified && (
                    <Badge variant="secondary" className="text-xs">Unverified</Badge>
                  )}
                  <Badge variant={u.role === "admin" ? "default" : "outline"}>
                    {u.role}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
