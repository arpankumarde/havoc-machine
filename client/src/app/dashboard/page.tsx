"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Image from "next/image";
import {
    BarChart3,
    Shield,
    Users,
    TrendingUp,
    AlertTriangle,
    LogOut,
    Activity
} from "lucide-react";

const DashboardPage = () => {
    const router = useRouter();
    const [userEmail, setUserEmail] = useState("");

    useEffect(() => {
        // Check authentication
        const isAuthenticated = localStorage.getItem("isAuthenticated");
        const email = localStorage.getItem("userEmail");

        if (!isAuthenticated || !email) {
            router.push("/login");
            return;
        }

        setUserEmail(email);
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem("isAuthenticated");
        localStorage.removeItem("userEmail");
        router.push("/login");
    };

    return (
        <div className="min-h-screen bg-[#1E1E1E] text-white">
            {/* Navigation */}
            <nav className="border-b border-[#B91C1C]/20 bg-[#1E1E1E]/80 backdrop-blur-sm sticky top-0 z-50">
                <div className="container mx-auto px-8 py-5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                    <div className="w-10 h-10 flex items-center justify-center">
  <Image
    src="/logo.png"
    alt="Logo"
    width={32}
    height={32}
    className="object-contain"
  />
</div>

                        <span className="text-2xl font-bold text-white cursor-pointer" onClick={() => router.push("/")}>HAVOC MACHINE</span>
                    </div>
                    <div className="flex items-center gap-6">
                        <span className="text-gray-300">Welcome, Admin</span>
                        <Button
                            onClick={handleLogout}
                            variant="outline"
                            className="border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                        >
                            <LogOut className="w-4 h-4 mr-2" />
                            Logout
                        </Button>
                    </div>
                </div>
            </nav>

            {/* Dashboard Content */}
            <div className="container mx-auto px-8 py-12">
                <div className="mb-8 flex items-start justify-between">
                    {/* Left: Heading */}
                    <div>
                        <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
                        <p className="text-gray-400">
                            Monitor your chaos testing results and system health
                        </p>
                    </div>

                    {/* Right: Run Test Button */}
                    <Link href="/dashboard/run">
                        <Button className="bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                            <Activity className="w-4 h-4 mr-2" />
                            Run Test
                        </Button>
                    </Link>
                </div>


                {/* Stats Grid */}
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Total Tests</CardTitle>
                            <Activity className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">1,247</div>
                            <p className="text-xs text-gray-400 mt-1">+12% from last month</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Vulnerabilities Found</CardTitle>
                            <AlertTriangle className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">23</div>
                            <p className="text-xs text-gray-400 mt-1">3 critical, 12 high</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Success Rate</CardTitle>
                            <TrendingUp className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">94.2%</div>
                            <p className="text-xs text-gray-400 mt-1">+2.1% improvement</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Active Agents</CardTitle>
                            <Users className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">8</div>
                            <p className="text-xs text-gray-400 mt-1">All systems operational</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Main Content Grid */}
                <div className="grid lg:grid-cols-3 gap-8">
                    {/* Recent Tests */}
                    <Card className="lg:col-span-2 bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader>
                            <CardTitle className="text-white">Recent Test Results</CardTitle>
                            <CardDescription className="text-gray-400">
                                Latest chaos testing sessions and their outcomes
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {[1, 2, 3, 4, 5].map((item) => (
                                    <div
                                        key={item}
                                        className="flex items-center justify-between p-4 bg-[#1E1E1E] border border-[#3A3A3A]"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 bg-[#B91C1C]/20 flex items-center justify-center">
                                                <Shield className="w-5 h-5 text-[#B91C1C]" />
                                            </div>
                                            <div>
                                                <p className="text-white font-medium">Policy Test #{1000 + item}</p>
                                                <p className="text-sm text-gray-400">Refund policy validation</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[#B91C1C] font-semibold">2 vulnerabilities</p>
                                            <p className="text-xs text-gray-400">2 hours ago</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Quick Actions */}
                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader>
                            <CardTitle className="text-white">Quick Actions</CardTitle>
                            <CardDescription className="text-gray-400">
                                Start a new test or view reports
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Link href="/dashboard/run">
                                <Button className="w-full bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0">
                                    <Activity className="w-4 h-4 mr-2" />
                                    Start New Test
                                </Button>
                            </Link>
                            <Button
                                variant="outline"
                                className="w-full border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                            >
                                <BarChart3 className="w-4 h-4 mr-2" />
                                View Reports
                            </Button>
                            <Button
                                variant="outline"
                                className="w-full border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                            >
                                <Shield className="w-4 h-4 mr-2" />
                                Policy Settings
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default DashboardPage;

