import { AuthForm } from "@/components/AuthForm";

export default function RegisterPage() {
  return <section className="narrow pageShell"><p className="eyebrow">Your private workspace</p><h1>Create your account</h1><AuthForm mode="register" /></section>;
}
