import { Redirect } from "expo-router";
import React from "react";

import { Loading } from "@/components/States";
import { useAuth } from "@/lib/auth";

export default function Index() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Starting Rent Manager…" />;
  if (!user) return <Redirect href="/login" />;
  return <Redirect href={user.role === "TENANT" ? "/(portal)" : "/(admin)"} />;
}
