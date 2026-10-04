import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "@/components/auth/AuthForm";

export const metadata: Metadata = { title: "Log in" };

export default function Page() {
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
