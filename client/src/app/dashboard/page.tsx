"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Image from "next/image";
import api from "@/utils/api";
import {
    BarChart3,
    Shield,
    Users,
    TrendingUp,
    AlertTriangle,
    LogOut,
    Activity,
    FileText,
    FileJson,
    Settings
} from "lucide-react";

interface Group {
    _id: string;
    group_id: string;
    session_ids: string[];
    websocket_url: string;
    parallel_executions: number;
    duration_minutes: number;
    adversarial_model: string | null;
    judge_model: string | null;
    status: "completed" | "running" | "failed";
    created_at: string;
    report_urls: {
        markdown: string | null;
        json: string | null;
    };
    completed_at?: string;
}

const DashboardPage = () => {
    const router = useRouter();
    const [userEmail, setUserEmail] = useState("");
    const [groups, setGroups] = useState<Group[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
    const [configWebsocketUrl, setConfigWebsocketUrl] = useState("ws://localhost:8000");
    const [configParallelExecutions, setConfigParallelExecutions] = useState(3);
    const [configDurationMinutes, setConfigDurationMinutes] = useState(1);
    const [showReportsModal, setShowReportsModal] = useState(false);

    useEffect(() => {
        // Check authentication
        const isAuthenticated = localStorage.getItem("isAuthenticated");
        const email = localStorage.getItem("userEmail");

        if (!isAuthenticated || !email) {
            router.push("/login");
            return;
        }

        setUserEmail(email);
        fetchGroups();
    }, [router]);

    const fetchGroups = async () => {
        try {
            setIsLoading(true);
            const response = await api.get("/api/groups");
            setGroups(response.data);
        } catch (error) {
            console.error("Error fetching groups:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    const getGroupIdWithoutPrefix = (groupId: string) => {
        return groupId.startsWith("grp-") ? groupId.substring(4) : groupId;
    };

    const handleSaveConfiguration = () => {
        // Save to localStorage for persistence (frontend only, no API call)
        localStorage.setItem("defaultWebsocketUrl", configWebsocketUrl);
        localStorage.setItem("defaultParallelExecutions", configParallelExecutions.toString());
        localStorage.setItem("defaultDurationMinutes", configDurationMinutes.toString());
        
        // Show success message
        alert("Configuration updated successfully!");
        setIsConfigModalOpen(false);
    };

    // Load default values from localStorage on mount
    useEffect(() => {
        const savedWebsocket = localStorage.getItem("defaultWebsocketUrl");
        const savedParallel = localStorage.getItem("defaultParallelExecutions");
        const savedDuration = localStorage.getItem("defaultDurationMinutes");
        
        if (savedWebsocket) setConfigWebsocketUrl(savedWebsocket);
        if (savedParallel) setConfigParallelExecutions(parseInt(savedParallel));
        if (savedDuration) setConfigDurationMinutes(parseFloat(savedDuration));
    }, []);

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
                            <div className="text-3xl font-bold text-white">{groups.length}</div>
                            <p className="text-xs text-gray-400 mt-1">Total test groups</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Completed</CardTitle>
                            <Shield className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">
                                {groups.filter(g => g.status === "completed").length}
                            </div>
                            <p className="text-xs text-gray-400 mt-1">Tests completed</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Running</CardTitle>
                            <TrendingUp className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">
                                {groups.filter(g => g.status === "running").length}
                            </div>
                            <p className="text-xs text-gray-400 mt-1">Active tests</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-400">Total Agents</CardTitle>
                            <Users className="w-4 h-4 text-[#B91C1C]" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">
                                {groups.reduce((sum, g) => sum + g.session_ids.length, 0)}
                            </div>
                            <p className="text-xs text-gray-400 mt-1">All sessions</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Main Content Grid */}
                <div className="grid lg:grid-cols-3 gap-8">
                    {/* Recent Tests */}
                    <Card className="lg:col-span-2 bg-[#252525] border-2 border-[#B91C1C]/30 border-0">
                        <CardHeader>
                            <CardTitle className="text-white">Test Groups</CardTitle>
                            <CardDescription className="text-gray-400">
                                Latest adversarial testing sessions and their outcomes
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex items-center justify-center py-12">
                                    <div className="text-gray-400">Loading groups...</div>
                                </div>
                            ) : groups.length === 0 ? (
                                <div className="flex items-center justify-center py-12">
                                    <div className="text-gray-400">No test groups found</div>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="border-[#3A3A3A]">
                                                <TableHead className="text-gray-300">Group ID</TableHead>
                                                <TableHead className="text-gray-300">Status</TableHead>
                                                <TableHead className="text-gray-300">Agents</TableHead>
                                                <TableHead className="text-gray-300">Duration</TableHead>
                                                <TableHead className="text-gray-300">Created</TableHead>
                                                <TableHead className="text-gray-300">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {groups.map((group) => (
                                                <TableRow key={group._id} className="border-[#3A3A3A]">
                                                    <TableCell className="text-white font-mono text-sm">
                                                        {group.group_id.length > 10 
                                                            ? group.group_id.substring(10) 
                                                            : group.group_id}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge
                                                            variant={
                                                                group.status === "completed"
                                                                    ? "default"
                                                                    : group.status === "running"
                                                                    ? "secondary"
                                                                    : "destructive"
                                                            }
                                                            className={
                                                                group.status === "completed"
                                                                    ? "bg-green-600 text-white"
                                                                    : group.status === "running"
                                                                    ? "bg-blue-600 text-white"
                                                                    : ""
                                                            }
                                                        >
                                                            {group.status}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="text-gray-300">
                                                        {group.session_ids.length}
                                                    </TableCell>
                                                    <TableCell className="text-gray-300">
                                                        {group.duration_minutes} min
                                                    </TableCell>
                                                    <TableCell className="text-gray-400 text-sm">
                                                        {formatDate(group.created_at)}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex gap-2">
                                                            {group.report_urls.markdown ? (
                                                                <Link
                                                                    href={`/dashboard/reports/${getGroupIdWithoutPrefix(group.group_id)}`}
                                                                >
                                                                    <Button
                                                                        size="sm"
                                                                        className="border-[#B91C1C] hover:bg-[#B91C1C] text-white h-8"
                                                                    >
                                                                        <FileText className="w-3 h-3 mr-1" />
                                                                        Report
                                                                    </Button>
                                                                </Link>
                                                            ) : null}
                                                            {group.report_urls.json ? (
                                                                <Button
                                                                    size="sm"
                                                                    variant="outline"
                                                                    className="border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white h-8"
                                                                    onClick={() => {
                                                                        window.open(
                                                                            group.report_urls.json!,
                                                                            "_blank"
                                                                        );
                                                                    }}
                                                                >
                                                                    <FileJson className="w-3 h-3 mr-1" />
                                                                    Logs
                                                                </Button>
                                                            ) : null}
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                            )}
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
                        <Button className="w-full bg-[#B91C1C] hover:bg-[#991B1B] text-white border-0" asChild>
                            <Link href="/dashboard/run">
                                <Activity className="w-4 h-4 mr-2" />
                                Start New Test
                            </Link>
                        </Button>
                            <Button
                                variant="outline"
                                className="w-full border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                                onClick={() => setShowReportsModal(true)}
                            >
                                <BarChart3 className="w-4 h-4 mr-2" />
                                View Reports
                            </Button>
                            <Button
                                variant="outline"
                                className="w-full border-2 border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                                onClick={() => setIsConfigModalOpen(true)}
                            >
                                <Settings className="w-4 h-4 mr-2" />
                                Configuration Update
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Configuration Update Modal */}
            <Dialog open={isConfigModalOpen} onOpenChange={setIsConfigModalOpen}>
                <DialogContent 
                    className="bg-[#252525] border-[#3A3A3A] text-white"
                    showCloseButton={true}
                >
                    <DialogHeader>
                        <DialogTitle className="text-white">Update Configuration</DialogTitle>
                        <DialogDescription className="text-gray-400">
                            Update default settings for adversarial tests
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="config_websocket_url" className="text-white">
                                WebSocket URL
                            </Label>
                            <Input
                                id="config_websocket_url"
                                type="text"
                                value={configWebsocketUrl}
                                onChange={(e) => setConfigWebsocketUrl(e.target.value)}
                                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                                placeholder="ws://localhost:8000"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="config_parallel_executions" className="text-white">
                                Parallel Executions
                            </Label>
                            <Input
                                id="config_parallel_executions"
                                type="number"
                                min="1"
                                value={configParallelExecutions}
                                onChange={(e) => setConfigParallelExecutions(parseInt(e.target.value) || 1)}
                                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="config_duration_minutes" className="text-white">
                                Duration (minutes)
                            </Label>
                            <Input
                                id="config_duration_minutes"
                                type="number"
                                min="0.1"
                                step="0.1"
                                value={configDurationMinutes}
                                onChange={(e) => setConfigDurationMinutes(parseFloat(e.target.value) || 1)}
                                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setIsConfigModalOpen(false)}
                            className="border-[#3A3A3A] text-gray-300 hover:bg-[#3A3A3A]"
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleSaveConfiguration}
                            className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
                        >
                            Save Configuration
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Reports Modal */}
            <Dialog open={showReportsModal} onOpenChange={setShowReportsModal}>
                <DialogContent 
                    className="bg-[#252525] border-[#3A3A3A] text-white max-w-4xl max-h-[80vh]"
                    showCloseButton={true}
                >
                    <DialogHeader>
                        <DialogTitle className="text-white">All Reports</DialogTitle>
                        <DialogDescription className="text-gray-400">
                            View and access all completed test reports
                        </DialogDescription>
                    </DialogHeader>
                    <div className="overflow-y-auto max-h-[60vh]">
                        {groups.filter(g => g.status === "completed" && g.report_urls.markdown).length === 0 ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="text-gray-400">No completed reports available</div>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {groups
                                    .filter(g => g.status === "completed" && g.report_urls.markdown)
                                    .map((group) => {
                                        const groupIdWithoutPrefix = getGroupIdWithoutPrefix(group.group_id);
                                        const displayGroupId = group.group_id.length > 10 
                                            ? group.group_id.substring(10) 
                                            : group.group_id;
                                        
                                        return (
                                            <div
                                                key={group._id}
                                                className="p-4 bg-[#1E1E1E] border border-[#3A3A3A] rounded-lg hover:border-[#B91C1C]/50 transition-colors"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-3 mb-2">
                                                            <div className="w-10 h-10 bg-[#B91C1C]/20 flex items-center justify-center rounded">
                                                                <FileText className="w-5 h-5 text-[#B91C1C]" />
                                                            </div>
                                                            <div>
                                                                <p className="text-white font-medium font-mono text-sm">
                                                                    {displayGroupId}
                                                                </p>
                                                                <p className="text-xs text-gray-400">
                                                                    {formatDate(group.created_at)}
                                                                </p>
                                                            </div>
                                                        </div>
                                                        <div className="flex gap-2 text-xs text-gray-400 ml-[52px]">
                                                            <span>{group.parallel_executions} agents</span>
                                                            <span>•</span>
                                                            <span>{group.duration_minutes} min</span>
                                                            {group.completed_at && (
                                                                <>
                                                                    <span>•</span>
                                                                    <span>Completed: {formatDate(group.completed_at)}</span>
                                                                </>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="flex gap-2 ml-4">
                                                        <Link href={`/dashboard/reports/${groupIdWithoutPrefix}`}>
                                                            <Button
                                                                size="sm"
                                                                className="border-[#B91C1C] hover:bg-[#B91C1C] text-white"
                                                            >
                                                                <FileText className="w-3 h-3 mr-1" />
                                                                Report
                                                            </Button>
                                                        </Link>
                                                        {group.report_urls.json && (
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                className="border-[#B91C1C] text-[#B91C1C] hover:bg-[#B91C1C] hover:text-white"
                                                                onClick={() => {
                                                                    window.open(
                                                                        group.report_urls.json!,
                                                                        "_blank"
                                                                    );
                                                                }}
                                                            >
                                                                <FileJson className="w-3 h-3 mr-1" />
                                                                Logs
                                                            </Button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default DashboardPage;

