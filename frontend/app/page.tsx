import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-5xl font-bold mb-4">Stock To Me</h1>
      <p className="text-muted-foreground text-lg mb-8 max-w-md text-center">
        SEC filing intelligence for small-cap traders. Monitor dilution risk, financing setups,
        and pump-before-offering patterns.
      </p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:opacity-90"
        >
          Sign In
        </Link>
        <Link
          href="/register"
          className="px-6 py-3 border border-border rounded-lg font-semibold hover:bg-muted"
        >
          Create Account
        </Link>
      </div>
      <p className="text-xs text-muted-foreground mt-16 max-w-sm text-center">
        For educational and informational purposes only. Not financial advice.
      </p>
    </div>
  );
}
