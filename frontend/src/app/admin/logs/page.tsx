"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminLogsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/admin/tasks");
  }, [router]);

  return null;
}
