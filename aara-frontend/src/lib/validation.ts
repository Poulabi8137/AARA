// RFC 5322-style email check: local part, single '@', domain with a TLD.
// Mirrors the backend's pydantic EmailStr (email-validator) behavior closely
// enough to reject obviously invalid input before it ever reaches the API.
const EMAIL_RE =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)+$/;

export function isValidEmail(email: string): boolean {
  const trimmed = email.trim();
  if (!trimmed || trimmed.length > 254) return false;
  if (!EMAIL_RE.test(trimmed)) return false;
  const domain = trimmed.split("@")[1] ?? "";
  return (
    domain.includes(".") && !domain.startsWith(".") && !domain.endsWith(".")
  );
}

export function getEmailError(email: string): string | null {
  if (!email.trim()) return "Email is required.";
  if (!isValidEmail(email)) return "Please enter a valid email address.";
  return null;
}

export interface PasswordRequirement {
  label: string;
  met: boolean;
}

export function getPasswordRequirements(
  password: string,
): PasswordRequirement[] {
  return [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One digit", met: /\d/.test(password) },
    { label: "One special character", met: /[^A-Za-z0-9]/.test(password) },
  ];
}

export function getPasswordError(password: string): string | null {
  const unmet = getPasswordRequirements(password).find((r) => !r.met);
  return unmet ? `Password is missing: ${unmet.label.toLowerCase()}.` : null;
}

export function isPasswordValid(password: string): boolean {
  return getPasswordRequirements(password).every((r) => r.met);
}
