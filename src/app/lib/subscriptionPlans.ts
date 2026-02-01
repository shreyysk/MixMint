export type SubscriptionPlan = "basic" | "pro" | "super";

export const SUBSCRIPTION_PLANS: Record<
  SubscriptionPlan,
  {
    track_quota: number;
    zip_quota: number;
    fan_upload_quota: number;
    duration_days: number;
  }
> = {
  basic: {
    track_quota: 5,
    zip_quota: 0,
    fan_upload_quota: 0,
    duration_days: 30,
  },
  pro: {
    track_quota: 20,
    zip_quota: 1,
    fan_upload_quota: 0,
    duration_days: 30,
  },
  super: {
    track_quota: 50,
    zip_quota: 2,
    fan_upload_quota: 10,
    duration_days: 30,
  },
};
