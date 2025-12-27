"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Shield, 
  Zap, 
  TrendingUp, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Target,
  DollarSign,
  Users,
  FileText,
  Globe,
  Brain,
  Lock,
  Rocket,
  LogOut,
  LayoutDashboard
} from "lucide-react";

const Page = () => {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    // Check authentication status
    const authStatus = localStorage.getItem("isAuthenticated");
    const email = localStorage.getItem("userEmail");
    
    if (authStatus === "true" && email) {
      setIsAuthenticated(true);
      setUserEmail(email);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("userEmail");
    setIsAuthenticated(false);
    setUserEmail("");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-[#1E1E1E] text-white">
      {/* Navigation */}
      <nav className="border-b border-[#B91C1C]/20 bg-[#1E1E1E]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-8 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#B91C1C] flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">HAVOC MACHINE</span>
          </div>
          <div className="flex items-center gap-8">
            <a href="#features" className="text-gray-300 hover:text-[#B91C1C] transition-colors">Features</a>
            <a href="#solution" className="text-gray-300 hover:text-[#B91C1C] transition-colors">Solution</a>
            <a href="#pricing" className="text-gray-300 hover:text-[#B91C1C] transition-colors">Pricing</a>
            {isAuthenticated ? (
              <>
                <Link href="/dashboard">
                  <Button 
                    className="border-2 border-[#B91C1C] text-[#1E1E1E] hover:bg-[#B91C1C] hover:text-white"
                  >
                    <LayoutDashboard className="w-4 h-4 mr-2" />
                    Dashboard
                  </Button>
                </Link>
                <Button 
                  onClick={handleLogout}
                  variant="outline" 
                  className="border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </Button>
              </>
            ) : (
              <Link href="/signup">
                <Button className="bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                  Get Started
                </Button>
              </Link>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden border-b-4 border-[#B91C1C]">
        <div className="absolute inset-0 bg-gradient-to-br from-[#1E1E1E] via-[#7F1D1D]/20 to-[#1E1E1E]"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(185,28,28,0.15),transparent_70%)]"></div>
        
        <div className="container mx-auto px-8 py-16 relative z-10">
          <div className="max-w-5xl mx-auto text-center">
            <Badge className="mb-8 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              <Sparkles className="w-3 h-3 mr-2" />
              Synthetic Customer Chaos Lab
            </Badge>
            
            <h1 className="text-6xl md:text-8xl font-black mb-8 leading-tight px-4">
              <span className="text-white">EXPLOIT</span>
              <br />
              <span className="text-[#B91C1C]">YOUR AI AGENTS</span>
              <br />
              <span className="text-white">BEFORE ATTACKERS DO</span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-300 mb-10 max-w-3xl mx-auto leading-relaxed px-4">
              AI-generated adversarial conversations expose policy loopholes, 
              refund leakage, and chatbot weaknesses before they impact real customers.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <Link href="/signup">
                <Button size="lg" className="bg-[#B91C1C] hover:bg-[#991B1B] text-white text-lg px-10 py-7 border-0">
                  Start Free Trial
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white text-lg px-10 py-7">
                Watch Demo
              </Button>
            </div>

            <div className="mt-20 grid grid-cols-3 gap-8 max-w-3xl mx-auto px-4">
              <div className="text-center">
                <div className="text-4xl font-bold text-[#B91C1C] mb-2">1,000+</div>
                <div className="text-sm text-gray-400">Conversations Generated</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-[#B91C1C] mb-2">$13B+</div>
                <div className="text-sm text-gray-400">Market Opportunity</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-[#B91C1C] mb-2">24/7</div>
                <div className="text-sm text-gray-400">Continuous Testing</div>
              </div>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#1E1E1E] to-transparent"></div>
      </section>

      {/* Problem Statement */}
      <section className="py-24 bg-[#1E1E1E] border-b border-[#B91C1C]/20">
        <div className="container mx-auto px-8">
          <div className="max-w-4xl mx-auto">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              The Challenge
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white leading-tight">
              The Gap Between Demo Performance and Real-World Resilience
            </h2>
            <p className="text-lg text-gray-300 leading-relaxed mb-12">
              Support operations face a critical gap between demo performance and real-world resilience. 
              Generative AI-powered chatbots excel in controlled environments but struggle under authentic 
              pressure scenarios including angry customers, code-mixed languages, incomplete information, 
              and deliberate policy exploitation.
            </p>
            <div className="grid md:grid-cols-3 gap-8 mt-12">
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <AlertTriangle className="w-8 h-8 text-[#B91C1C] mb-4" />
                  <CardTitle className="text-white">Inconsistent Policy</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Current testing methods cannot economically simulate thousands of realistic support 
                    conversations to identify weak points.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <DollarSign className="w-8 h-8 text-[#B91C1C] mb-4" />
                  <CardTitle className="text-white">Revenue Leakage</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Exploited loopholes result in revenue leakage through refund policies, replacement 
                    workflows, and COD return handling.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <Users className="w-8 h-8 text-[#B91C1C] mb-4" />
                  <CardTitle className="text-white">Brand Trust Erosion</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Degraded customer experiences erode brand trust when support systems fail under 
                    real-world pressure.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Architecture */}
      <section id="solution" className="py-24 bg-[#1E1E1E]">
        <div className="container mx-auto px-8">
          <div className="text-center mb-20">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              Our Solution
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Three-Pillar Architecture
            </h2>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              A comprehensive platform that transforms how you test and secure your customer support systems
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-10 max-w-6xl mx-auto">
            <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 p-8 hover:border-[#DC2626] transition-colors">
              <CardHeader>
                <div className="w-16 h-16 bg-[#B91C1C] flex items-center justify-center mb-6">
                  <FileText className="w-8 h-8 text-white" />
                </div>
                <CardTitle className="text-2xl text-white mb-4">Core Platform</CardTitle>
                <CardDescription className="text-gray-400">
                  Web-based simulation engine that ingests product catalogs and policy documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>SKU and pricing management</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Refund rules and replacement criteria</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>COD terms and exception handling</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 p-8 hover:border-[#DC2626] transition-colors">
              <CardHeader>
                <div className="w-16 h-16 bg-[#B91C1C] flex items-center justify-center mb-6">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <CardTitle className="text-2xl text-white mb-4">AI-Powered Chaos</CardTitle>
                <CardDescription className="text-gray-400">
                  Generative AI creates adversarial customer personas that test policy boundaries
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Emotional escalation tactics</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Language switching mid-conversation</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Creative policy interpretation</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 p-8 hover:border-[#DC2626] transition-colors">
              <CardHeader>
                <div className="w-16 h-16 bg-[#B91C1C] flex items-center justify-center mb-6">
                  <BarChart3 className="w-8 h-8 text-white" />
                </div>
                <CardTitle className="text-2xl text-white mb-4">Evaluation Framework</CardTitle>
                <CardDescription className="text-gray-400">
                  Automated scoring across policy compliance and empathy dimensions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Policy compliance scoring</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Tone analysis and empathy index</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>De-escalation technique evaluation</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section id="features" className="py-24 bg-[#1E1E1E] border-t border-[#B91C1C]/20">
        <div className="container mx-auto px-8">
          <div className="text-center mb-20">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              Features
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Comprehensive Testing Platform
            </h2>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              Three phases of powerful features designed to protect your business
            </p>
          </div>

          {/* Phase 1 */}
          <div className="mb-20">
            <div className="flex items-center gap-4 mb-10">
              <div className="w-12 h-12 bg-[#B91C1C] flex items-center justify-center text-white font-bold text-xl">
                1
              </div>
              <h3 className="text-3xl font-bold text-white">Phase 1: Core Testing Platform</h3>
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Zap className="w-6 h-6 text-[#B91C1C]" />
                    Mass Scenario Generation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Generate 1,000+ unique conversation scenarios from a single policy document. 
                    Each scenario tests different edge cases and policy interpretations.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Globe className="w-6 h-6 text-[#B91C1C]" />
                    Multi-Language Chaos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Inject chaos in English, Hindi, Hinglish, and Tamil. Test your support systems 
                    against code-mixed languages and regional variations.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Shield className="w-6 h-6 text-[#B91C1C]" />
                    Real-Time Violation Detection
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Instant policy violation detection with detailed annotations. Know exactly where 
                    and why your policies are being exploited.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Target className="w-6 h-6 text-[#B91C1C]" />
                    Conversation Replay
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Full conversation replay with failure annotations. Review every interaction 
                    that led to policy breaches or system failures.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Phase 2 */}
          <div className="mb-20">
            <div className="flex items-center gap-4 mb-10">
              <div className="w-12 h-12 bg-[#B91C1C] flex items-center justify-center text-white font-bold text-xl">
                2
              </div>
              <h3 className="text-3xl font-bold text-white">Phase 2: Analytics Dashboard</h3>
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <AlertTriangle className="w-6 h-6 text-[#B91C1C]" />
                    Top Failure Intents
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Ranked list of scenarios causing the highest policy breaches. Identify your 
                    most vulnerable support workflows and prioritize fixes.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <DollarSign className="w-6 h-6 text-[#B91C1C]" />
                    Refund Leakage Risk Score
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Financial impact projection based on detected vulnerabilities. Understand the 
                    potential revenue loss from each policy gap.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-[#B91C1C]" />
                    Exploit Pattern Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Common customer tactics that successfully bypass controls. Learn how adversaries 
                    exploit your policies and prepare defenses.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <FileText className="w-6 h-6 text-[#B91C1C]" />
                    Suggested Policy Rewrites
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">
                    Natural language recommendations to tighten loopholes. Get actionable suggestions 
                    for improving your policy documents.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Phase 3 */}
          <div>
            <div className="flex items-center gap-4 mb-10">
              <div className="w-12 h-12 bg-[#B91C1C] flex items-center justify-center text-white font-bold text-xl">
                3
              </div>
              <h3 className="text-3xl font-bold text-white">Phase 3: Policy Patch Generator</h3>
              <Badge className="bg-[#B91C1C] text-white border-0 px-4 py-1">Hackathon Innovation</Badge>
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Lock className="w-6 h-6 text-[#B91C1C]" />
                    Automated Policy Diffs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400 mb-4">
                    Automatically generates policy document diffs showing exact sentences to add or modify. 
                    Targets the top 3 exploited loopholes from test results.
                  </p>
                  <ul className="space-y-2 text-gray-300">
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                      <span>Before/after comparison with predicted leakage reduction</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                      <span>Implementation priority ranking</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                      <span>Complete testing-to-fix workflow</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
              <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 p-6">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Rocket className="w-6 h-6 text-[#B91C1C]" />
                    Competitive Advantage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400 mb-4">
                    Unlike traditional load testing that focuses on infrastructure resilience, 
                    Havoc Machine targets business logic vulnerabilities in customer support workflows.
                  </p>
                  <p className="text-gray-400">
                    The Policy Patch Generator provides actionable remediation, not just problem 
                    identification, creating a complete testing-to-fix workflow that chaos engineering 
                    tools typically lack.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Target Market */}
      <section className="py-24 bg-[#1E1E1E] border-t border-[#B91C1C]/20">
        <div className="container mx-auto px-8">
          <div className="text-center mb-20">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              Who We Serve
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Built for Support Excellence
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-10 max-w-6xl mx-auto">
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-8">
              <CardHeader>
                <div className="w-20 h-20 bg-[#B91C1C] mx-auto mb-6 flex items-center justify-center">
                  <Users className="w-10 h-10 text-white" />
                </div>
                <CardTitle className="text-2xl text-white">D2C E-commerce Brands</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-400">
                  Fashion, electronics, and FMCG companies with high return rates. Protect your 
                  revenue from policy exploitation and ensure consistent customer experiences.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-8">
              <CardHeader>
                <div className="w-20 h-20 bg-[#B91C1C] mx-auto mb-6 flex items-center justify-center">
                  <Shield className="w-10 h-10 text-white" />
                </div>
                <CardTitle className="text-2xl text-white">Support Platform Agencies</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-400">
                  BPOs and customer service consultancies managing multiple brands. Scale your 
                  quality assurance across all client accounts with automated testing.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-8">
              <CardHeader>
                <div className="w-20 h-20 bg-[#B91C1C] mx-auto mb-6 flex items-center justify-center">
                  <Brain className="w-10 h-10 text-white" />
                </div>
                <CardTitle className="text-2xl text-white">Chatbot Vendors</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-400">
                  AI platform providers needing pre-deployment validation tools. Ensure your 
                  chatbots are production-ready before they face real customers.
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="mt-20 text-center">
            <Card className="bg-[#252525] border-4 border-[#B91C1C] border-0 max-w-3xl mx-auto p-8">
              <CardContent>
                <p className="text-xl text-gray-300 mb-4">
                  The global generative AI market for customer support exceeds{" "}
                  <span className="text-[#B91C1C] font-bold text-2xl">$13 billion</span> and is rapidly expanding
                </p>
                <p className="text-gray-400">
                  Organizations are seeking tools to ensure 24/7 support reliability and protect 
                  their revenue from policy vulnerabilities.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 bg-[#1E1E1E] border-t border-[#B91C1C]/20">
        <div className="container mx-auto px-8">
          <div className="text-center mb-20">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              Pricing
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Choose Your Plan
            </h2>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              Start free and scale as you grow. All plans include core testing capabilities.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-10 max-w-6xl mx-auto">
            {/* Freemium */}
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
              <CardHeader>
                <CardTitle className="text-2xl text-white mb-2">Freemium</CardTitle>
                <CardDescription className="text-gray-400">Perfect for getting started</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-white">$0</span>
                  <span className="text-gray-400">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>100 free test conversations per month</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Basic scenario generation</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Policy violation detection</span>
                  </li>
                </ul>
                <Link href="/signup" className="w-full">
                  <Button className="w-full bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                    Get Started Free
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Pro */}
            <Card className="bg-[#1E1E1E] border-4 border-[#B91C1C] border-0 relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <Badge className="bg-[#B91C1C] text-white border-0 px-4 py-1">Most Popular</Badge>
              </div>
              <CardHeader>
                <CardTitle className="text-2xl text-white mb-2">Pro</CardTitle>
                <CardDescription className="text-gray-400">For growing businesses</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-white">$299</span>
                  <span className="text-gray-400">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>10,000 simulations per month</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Basic analytics dashboard</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Multi-language support</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Priority email support</span>
                  </li>
                </ul>
                <Button className="w-full bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                  Start Pro Trial
                </Button>
              </CardContent>
            </Card>

            {/* Enterprise */}
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 p-6">
              <CardHeader>
                <CardTitle className="text-2xl text-white mb-2">Enterprise</CardTitle>
                <CardDescription className="text-gray-400">Custom solutions</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-white">Custom</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Unlimited simulations</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Policy Patch Generator</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>White-label deployment</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>API access</span>
                  </li>
                  <li className="flex items-start gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-[#B91C1C] mt-0.5 flex-shrink-0" />
                    <span>Professional services & consulting</span>
                  </li>
                </ul>
                <Button className="w-full bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                  Contact Sales
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Success Metrics */}
      <section className="py-24 bg-[#1E1E1E] border-t border-[#B91C1C]/20">
        <div className="container mx-auto px-8">
          <div className="text-center mb-20">
            <Badge className="mb-6 bg-[#B91C1C]/20 text-[#DC2626] border-[#B91C1C]/50 border-0 px-4 py-2">
              Impact
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Measurable Results
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-8 max-w-6xl mx-auto">
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-6">
              <CardContent>
                <div className="text-3xl font-bold text-[#B91C1C] mb-2">1,000+</div>
                <div className="text-sm text-gray-400">Conversations per engagement</div>
              </CardContent>
            </Card>
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-6">
              <CardContent>
                <div className="text-3xl font-bold text-[#B91C1C] mb-2">90%+</div>
                <div className="text-sm text-gray-400">Vulnerabilities detected pre-production</div>
              </CardContent>
            </Card>
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-6">
              <CardContent>
                <div className="text-3xl font-bold text-[#B91C1C] mb-2">$XXXK</div>
                <div className="text-sm text-gray-400">Refund leakage prevented</div>
              </CardContent>
            </Card>
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-6">
              <CardContent>
                <div className="text-3xl font-bold text-[#B91C1C] mb-2">50%</div>
                <div className="text-sm text-gray-400">Faster time-to-fix</div>
              </CardContent>
            </Card>
            <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0 text-center p-6">
              <CardContent>
                <div className="text-3xl font-bold text-[#B91C1C] mb-2">2x</div>
                <div className="text-sm text-gray-400">Customer retention improvement</div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-[#1E1E1E] border-t-4 border-[#B91C1C]">
        <div className="container mx-auto px-8">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-white">
              Ready to Protect Your Support System?
            </h2>
            <p className="text-xl text-gray-300 mb-10">
              Start testing with 100 free conversations. No credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/signup">
                <Button size="lg" className="bg-[#B91C1C] hover:bg-[#991B1B] text-white text-lg px-10 py-7 border-0">
                  Start Free Trial
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white text-lg px-10 py-7">
                Schedule Demo
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#1E1E1E] border-t border-[#B91C1C]/20 py-16">
        <div className="container mx-auto px-8">
          <div className="grid md:grid-cols-4 gap-10 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-6">
                <div className="w-8 h-8 bg-[#B91C1C] flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">HAVOC MACHINE</span>
              </div>
              <p className="text-gray-400 text-sm">
                Synthetic Customer Chaos Lab for stress-testing support systems.
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Product</h4>
              <ul className="space-y-3 text-gray-400 text-sm">
                <li><a href="#features" className="hover:text-[#B91C1C] transition-colors">Features</a></li>
                <li><a href="#solution" className="hover:text-[#B91C1C] transition-colors">Solution</a></li>
                <li><a href="#pricing" className="hover:text-[#B91C1C] transition-colors">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Company</h4>
              <ul className="space-y-3 text-gray-400 text-sm">
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">About</a></li>
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Support</h4>
              <ul className="space-y-3 text-gray-400 text-sm">
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">Contact</a></li>
                <li><a href="#" className="hover:text-[#B91C1C] transition-colors">Privacy</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-[#B91C1C]/20 pt-8 text-center text-gray-400 text-sm">
            <p>© 2024 Havoc Machine. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Page;
