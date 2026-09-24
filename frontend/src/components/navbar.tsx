"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/auth";
import { Button, buttonVariants } from "@/components/ui/button";

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const navLink = (href: string, label: string) => (
    <Link
      key={href}
      href={href}
      className={`text-sm font-medium transition-colors hover:text-foreground/80 ${
        pathname === href ? "text-foreground" : "text-foreground/60"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-backdrop-blur:bg-background/60">
      <div className="max-w-6xl mx-auto px-4 flex h-14 items-center justify-between">
        <Link href="/" className="font-semibold text-sm tracking-tight">
          ResumeReviewerDV
        </Link>

        <nav className="flex items-center gap-6">
          {user ? (
            <>
              {navLink("/dashboard", "Dashboard")}
              {navLink("/submit", "Submit Resume")}
              {user.role === "admin" && (
                <>
                  {navLink("/admin/profiles", "Profiles")}
                  {navLink("/admin/submissions", "All Submissions")}
                  {navLink("/admin/users", "Users")}
                </>
              )}
              <Button variant="outline" size="sm" onClick={() => logout()}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              {navLink("/login", "Sign in")}
              <Link href="/signup" className={buttonVariants({ size: "sm" })}>
                Get started
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
