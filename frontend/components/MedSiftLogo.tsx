"use client";

import Image from "next/image";

interface MedSiftLogoProps {
  variant?: "full" | "icon";
  className?: string;
  height?: number;
}

/**
 * MedSift AI official brand logo (PNG from public/logo.png).
 */
export function MedSiftLogo({ variant = "full", className = "", height = 40 }: MedSiftLogoProps) {
  const width = variant === "full" ? Math.round(height * 1.5) : height;

  return (
    <Image
      src="/logo.png"
      alt="MedSift AI"
      width={width}
      height={height}
      className={`object-contain ${className}`}
      style={{ mixBlendMode: "multiply" }}
      priority
    />
  );
}
