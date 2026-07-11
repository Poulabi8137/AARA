"use client";

import { useToast as useToastPrimitive } from "@/components/ui/use-toast";

export function useToast() {
  return useToastPrimitive();
}
