import { AuthForm } from "@/components/AuthForm";

export default function LoginPage() {
  return <section className="narrow pageShell"><p className="eyebrow">Welcome back</p><h1>Sign in</h1><AuthForm mode="login" /></section>;
}
