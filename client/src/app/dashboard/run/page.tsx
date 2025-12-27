"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, Home, Play, LogOut } from "lucide-react";
import { Streamdown } from "streamdown";
import Image from "next/image";
import api from "@/utils/api";
import { useState, useEffect, useRef } from "react";
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

interface Message {
  timestamp: string;
  type: "human" | "ai";
  content: string;
}

interface SessionMessages {
  session_id: string;
  message_count: number;
  messages: Message[];
}

const RunPage = () => {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(true);
  const [websocketUrl, setWebsocketUrl] = useState("ws://localhost:8000");
  const [parallelExecutions, setParallelExecutions] = useState(3);
  const [durationMinutes, setDurationMinutes] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [groupId, setGroupId] = useState<string | null>(null);
  const [sessionIds, setSessionIds] = useState<string[]>([]);
  const [sessionMessages, setSessionMessages] = useState<Record<string, Message[]>>({});
  const [isPolling, setIsPolling] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const sessionPollingIntervalsRef = useRef<Record<string, NodeJS.Timeout>>({});
  const testDurationRef = useRef<number>(1);

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("userEmail");
    router.push("/login");
  };

  const handleStart = async () => {
    setIsLoading(true);
    try {
      const response = await api.post("/api/adversarial/parallel", {
        websocket_url: websocketUrl,
        parallel_executions: parallelExecutions,
        duration_minutes: durationMinutes,
      });

      const { group_id, session_ids, status, message } = response.data;
      setGroupId(group_id);
      testDurationRef.current = durationMinutes;
      setSessionIds(session_ids);
      setIsModalOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error("Error starting adversarial test:", error);
      setIsLoading(false);
      alert("Failed to start adversarial test. Please check the server connection.");
    }
  };

  const startPolling = (sessionIdsToPoll: string[], duration: number) => {
    setIsPolling(true);
    const pollDuration = (duration + 0.5) * 60 * 1000; // duration_minutes + 30 seconds in milliseconds
    const endTime = Date.now() + pollDuration;

    // Poll each session for messages
    sessionIdsToPoll.forEach((sessionId) => {
      // Initial fetch
      fetchSessionMessages(sessionId);
      
      const interval = setInterval(() => {
        if (Date.now() < endTime) {
          fetchSessionMessages(sessionId);
        } else {
          clearInterval(interval);
          delete sessionPollingIntervalsRef.current[sessionId];
        }
      }, 6000); // Poll every 6 seconds

      sessionPollingIntervalsRef.current[sessionId] = interval;
    });

    // Stop all polling after duration + 30 seconds
    setTimeout(() => {
      Object.values(sessionPollingIntervalsRef.current).forEach((interval) => {
        clearInterval(interval);
      });
      sessionPollingIntervalsRef.current = {};
      setIsPolling(false);
      setShowCompletionModal(true);
    }, pollDuration);
  };

  const fetchSessionMessages = async (sessionId: string) => {
    try {
      const response = await api.get(`/api/session/${sessionId}/messages`);
      const data: SessionMessages = response.data;
      
      // Messages are in descending order (newest first), so reverse for display
      const reversedMessages = [...data.messages].reverse();
      setSessionMessages((prev) => ({
        ...prev,
        [sessionId]: reversedMessages,
      }));
    } catch (error) {
      console.error(`Error fetching messages for session ${sessionId}:`, error);
    }
  };

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      Object.values(sessionPollingIntervalsRef.current).forEach((interval) => {
        clearInterval(interval);
      });
    };
  }, []);

  // Start polling when sessionIds are set
  useEffect(() => {
    if (sessionIds.length > 0 && !isPolling) {
      startPolling(sessionIds, testDurationRef.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionIds]);

  const aiProviders = sessionIds.length > 0
    ? sessionIds.map((sessionId, i) => ({
        id: sessionId,
        name: `Activity ${i + 1}`,
        color: "text-[#B91C1C]",
      }))
    : Array.from({ length: 4 }, (_, i) => ({
        id: `activity-${i + 1}`,
        name: `Activity ${i + 1}`,
        color: "text-[#B91C1C]",
      }));

  const getMessagesForActivity = (activityId: string): Message[] => {
    return sessionMessages[activityId] || [];
  };

  const handleOpenReport = () => {
    if (groupId) {
      // Remove "grp-" prefix from group_id
      const groupIdWithoutPrefix = groupId.startsWith("grp-") 
        ? groupId.substring(4) 
        : groupId;
      window.open(
        `https://sprintingn.s3.amazonaws.com/havoc-machine/${groupIdWithoutPrefix}.md`,
        "_blank"
      );
    }
  };

  const handleOpenLogs = () => {
    if (groupId) {
      // Remove "grp-" prefix from group_id
      const groupIdWithoutPrefix = groupId.startsWith("grp-") 
        ? groupId.substring(4) 
        : groupId;
      window.open(
        `https://sprintingn.s3.amazonaws.com/havoc-machine/${groupIdWithoutPrefix}.json`,
        "_blank"
      );
    }
  };

  return (
    <div className="min-h-screen bg-[#1E1E1E] text-white flex">
      {/* Completion Modal */}
      <Dialog open={showCompletionModal} onOpenChange={setShowCompletionModal}>
        <DialogContent 
          className="bg-[#252525] border-[#3A3A3A] text-white"
          showCloseButton={true}
        >
          <DialogHeader>
            <DialogTitle className="text-white">Adverse Testing completed</DialogTitle>
            <DialogDescription className="text-gray-400">
              The adversarial test has finished. You can now view the report and logs.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2 sm:gap-0">
            <Button
              onClick={handleOpenReport}
              className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
            >
              Open Report
            </Button>
            <Button
              onClick={handleOpenLogs}
              className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
            >
              Open Logs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Configuration Modal */}
      <Dialog 
        open={isModalOpen} 
        onOpenChange={(open) => {
          // Prevent closing while loading or during test
          if (!isLoading && !isPolling) {
            setIsModalOpen(open);
          }
        }}
      >
        <DialogContent 
          className="bg-[#252525] border-[#3A3A3A] text-white"
          showCloseButton={!isLoading && !isPolling}
        >
          <DialogHeader>
            <DialogTitle className="text-white">Start Adversarial Test</DialogTitle>
            <DialogDescription className="text-gray-400">
              Configure the parameters for the parallel adversarial test
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="websocket_url" className="text-white">
                WebSocket URL
              </Label>
              <Input
                id="websocket_url"
                type="text"
                value={websocketUrl}
                onChange={(e) => setWebsocketUrl(e.target.value)}
                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                placeholder="ws://localhost:8000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="parallel_executions" className="text-white">
                Parallel Executions
              </Label>
              <Input
                id="parallel_executions"
                type="number"
                min="1"
                value={parallelExecutions}
                onChange={(e) => setParallelExecutions(parseInt(e.target.value) || 1)}
                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="duration_minutes" className="text-white">
                Duration (minutes)
              </Label>
              <Input
                id="duration_minutes"
                type="number"
                min="0.1"
                step="0.1"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(parseFloat(e.target.value) || 1)}
                className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleStart}
              disabled={isLoading}
              className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
            >
              {isLoading ? "Starting..." : "Start Test"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Fixed Sidebar */}
      <aside className="w-20 bg-[#252525] border-r border-[#B91C1C]/20 flex flex-col fixed h-screen">
        {/* Logo */}
        <div className="p-4 border-b border-[#B91C1C]/20 flex justify-center">
        <div className="w-10 h-10 flex items-center justify-center">
  <Image
    src="/logo.png"
    alt="Logo"
    width={32}
    height={32}
    className="object-contain"
  />
</div>

        </div>

        {/* Navigation Icons */}
        <nav className="flex-1 p-3 space-y-3 flex flex-col items-center">
          <Link href="/dashboard">
            <Button
              variant="ghost"
              className="
        w-12 h-12
        flex items-center justify-center
        text-gray-300
        hover:text-white
        hover:bg-[#B91C1C]/20
      "
            >
              <LayoutDashboard className="w-5 h-5" />
            </Button>
          </Link>

          <Link href="/dashboard/run">
            <Button
              variant="ghost"
              className="
        w-12 h-12
        flex items-center justify-center
        text-white
        bg-[#B91C1C]/20
        hover:bg-[#B91C1C]/30
      "
            >
              <Play className="w-5 h-5" />
            </Button>
          </Link>

          <Link href="/">
            <Button
              variant="ghost"
              className="
        w-12 h-12
        flex items-center justify-center
        text-gray-300
        hover:text-white
        hover:bg-[#B91C1C]/20
      "
            >
              <Home className="w-5 h-5" />
            </Button>
          </Link>
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-[#B91C1C]/20 flex justify-center">
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="
      w-12 h-12
      flex items-center justify-center
      text-gray-300
      hover:text-white
      hover:bg-[#B91C1C]/20"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="h-screen w-full ml-20 bg-[#1E1E1E] overflow-hidden">
        <div className="h-full overflow-x-auto">
          <div className="flex h-full min-w-max">
            {aiProviders.map((ai) => {
              const messages = getMessagesForActivity(ai.id);
              return (
                <div
                  key={ai.id}
                  className="
            w-[420px]
            h-full
            flex-shrink-0
            border-r border-gray-300
            flex flex-col
            bg-[#252525]
          "
                >
                  {/* Top AI Bar */}
                  <div className="h-14 px-4 flex items-center justify-between border-b border-gray-500">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full bg-current ${ai.color}`}
                      />
                      <span className="text-sm font-medium text-white">
                        {ai.name}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {isPolling ? "Running" : "Online"}
                    </span>
                  </div>

                  {/* Chat Messages */}
                  <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                    {messages.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                        Waiting for messages...
                      </div>
                    ) : (
                      messages.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`flex ${
                            msg.type === "human" ? "justify-end" : "justify-start"
                          }`}
                        >
                          <div
                            className={`
    max-w-[85%]
    px-4 py-3
    text-sm
    rounded-2xl
    ${
      msg.type === "human"
        ? "bg-[#B91C1C] text-white rounded-br-md"
        : "bg-[#1E1E1E] text-gray-300 border border-[#3A3A3A] rounded-bl-md"
    }
  `}
                          >
                            <div className="streamdown">
                              <Streamdown>{msg.content}</Streamdown>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
};

export default RunPage;
