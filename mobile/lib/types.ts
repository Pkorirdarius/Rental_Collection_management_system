export type Role = "ADMIN" | "CARETAKER" | "TENANT";

export interface User {
  id: string;
  email: string;
  phone: string | null;
  full_name: string;
  role: Role;
  organization: string | null;
  organization_name: string;
  totp_enabled: boolean;
  must_change_password: boolean;
  is_active: boolean;
  date_joined: string;
}

export interface AuthSession {
  access: string;
  refresh: string;
  user: User;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardSummary {
  month: string;
  expected: string;
  rent_expected: string;
  late_fees: string;
  collected: string;
  collection_rate: number;
  arrears: string;
  active_tenants: number;
  active_leases: number;
  units: number;
  occupied_units: number;
  occupancy_rate: number;
  status_counts: { PAID: number; PARTIAL: number; OVERDUE: number };
  unmatched_payments: number;
  open_promises: number;
}

export interface OverdueTenant {
  lease_id: string;
  tenant_id: string;
  tenant: string;
  phone: string;
  property: string;
  unit: string;
  rent: string;
  balance: string;
  status: string;
  days_overdue: number;
  buckets: Record<string, string>;
  promise: { amount: string; date: string; note: string } | null;
}

export interface Lease {
  id: string;
  tenant: string;
  tenant_name: string;
  tenant_phone: string;
  unit: string;
  unit_code: string;
  property_name: string;
  property_id: string;
  start_date: string;
  end_date: string | null;
  rent_amount: string;
  due_day: number;
  grace_period_days: number;
  deposit_amount: string;
  deposit_paid: string;
  status: string;
  balance: string;
  days_overdue: number;
  payment_status: string;
  notes: string;
}

export interface TenantUnit {
  id: string;
  code: string;
  property: string;
  bill_ref: string;
}

export interface Tenant {
  id: string;
  full_name: string;
  phone: string;
  alt_phone: string;
  email: string;
  national_id: string;
  emergency_contact: string;
  notes: string;
  status: string;
  portal_enabled: boolean;
  active_lease_id: string | null;
  unit: TenantUnit | null;
  balance: string | null;
  lease_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  tenant: string | null;
  tenant_name: string;
  lease: string | null;
  unit: string | null;
  unit_code: string;
  property_name: string;
  method: string;
  amount: string;
  status: string;
  paid_at: string;
  reference: string;
  provider_txn_id: string;
  phone: string;
  bill_ref: string;
  received_by: string | null;
  received_by_name: string;
  matched_by: string | null;
  matched_at: string | null;
  notes: string;
  match_note: string;
  photo: string | null;
  receipt_number: string;
  has_receipt: boolean;
  created_at: string;
}

export interface PortalProfile {
  id: string;
  full_name: string;
  phone: string;
  email: string;
  lease_id: string | null;
  property: string | null;
  unit: string | null;
  rent_amount: string | null;
  due_day: number | null;
  balance: string;
  status: string;
  days_overdue: number;
  bill_ref: string | null;
}

export interface PortalLeaseBalance {
  lease_id: string;
  property: string;
  unit: string;
  rent_amount: string;
  balance: string;
  status: string;
  days_overdue: number;
}

export interface PortalReceipt {
  payment_id: string;
  receipt_number: string;
  amount: string;
  paid_at: string;
  download: string;
}

export interface StatementEntry {
  id: string;
  date: string;
  type: string;
  description: string;
  debit: string;
  credit: string;
  balance: string;
  reference: string;
}

export interface LeaseStatement {
  lease_id: string;
  tenant: string;
  unit: string;
  property: string;
  balance: string;
  status: string;
  days_overdue: number;
  entries: StatementEntry[];
}

export interface TenantStatement {
  tenant_id: string;
  tenant: string;
  phone: string;
  leases: LeaseStatement[];
  total_balance: string;
}

export interface ReminderSetting {
  enabled: boolean;
  pre_due_days: number;
  escalation_offsets: number[];
  send_hour: number;
  language: "en" | "sw";
  sender_id: string;
  updated_at: string;
}

export interface ExpectedVsCollected {
  month: string;
  expected: string;
  collected: string;
  difference: string;
  rate: number;
}

export interface OccupancyRow {
  property_id: string;
  property: string;
  units: number;
  occupied: number;
  vacant: number;
  maintenance: number;
  occupancy_rate: number;
}

export interface ArrearsAgeing {
  totals: Record<string, string>;
  by_property: Record<string, Record<string, string>>;
  total_outstanding: string;
}

export interface LeaseOption {
  id: string;
  tenant_name: string;
  unit_code: string;
  property_name: string;
  balance: string;
  status: string;
}
