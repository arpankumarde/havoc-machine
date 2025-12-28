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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

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

const processingMessages = [
  "Chats have been processed",
  "Processing the logs",
  "Building comprehensive report",
  "Uploading reports to storage",
  "Finalizing analysis"
];

const RunPage = () => {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("form");
  const [jsonInput, setJsonInput] = useState("");
  const [websocketUrl, setWebsocketUrl] = useState("ws://localhost:8000");
  const [parallelExecutions, setParallelExecutions] = useState(3);
  const [durationMinutes, setDurationMinutes] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [groupId, setGroupId] = useState<string | null>(null);
  const [sessionIds, setSessionIds] = useState<string[]>([]);
  const [sessionMessages, setSessionMessages] = useState<Record<string, Message[]>>({});
  const [isPolling, setIsPolling] = useState(false);
  const [showProcessingModal, setShowProcessingModal] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [processingStatus, setProcessingStatus] = useState(0);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const sessionPollingIntervalsRef = useRef<Record<string, NodeJS.Timeout>>({});
  const testDurationRef = useRef<number>(1);
  const abortControllersRef = useRef<Record<string, AbortController>>({});
  const chatContainerRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const previousMessageCountsRef = useRef<Record<string, number>>({});

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("userEmail");
    router.push("/login");
  };

  const validateJsonConfig = (jsonStr: string): { valid: boolean; data?: any; error?: string } => {
    try {
      const parsed = JSON.parse(jsonStr);
      const requiredKeys = ["websocket_url", "parallel_executions", "duration_minutes"];
      const missingKeys = requiredKeys.filter(key => !(key in parsed));
      
      if (missingKeys.length > 0) {
        return {
          valid: false,
          error: `Missing required keys: ${missingKeys.join(", ")}`
        };
      }
      
      // Validate limits
      if (parsed.parallel_executions > 5) {
        return {
          valid: false,
          error: "Parallel executions cannot exceed 5. Please upgrade your plan to use more parallel executions."
        };
      }
      
      if (parsed.duration_minutes > 5) {
        return {
          valid: false,
          error: "Duration cannot exceed 5 minutes. Please upgrade your plan to run longer tests."
        };
      }
      
      return { valid: true, data: parsed };
    } catch (error) {
      return {
        valid: false,
        error: "Invalid JSON format"
      };
    }
  };

  const validateLimits = (parallelExecutions: number, durationMinutes: number): { valid: boolean; error?: string } => {
    if (parallelExecutions > 5) {
      return {
        valid: false,
        error: "Parallel executions cannot exceed 5. Please upgrade your plan to use more parallel executions."
      };
    }
    
    if (durationMinutes > 5) {
      return {
        valid: false,
        error: "Duration cannot exceed 5 minutes. Please upgrade your plan to run longer tests."
      };
    }
    
    return { valid: true };
  };

  const handleStart = async () => {
    let config: {
      websocket_url: string;
      parallel_executions: number;
      duration_minutes: number;
    };

    // Get config from either form or JSON
    if (activeTab === "json") {
      const validation = validateJsonConfig(jsonInput);
      if (!validation.valid) {
        alert(validation.error || "Invalid configuration");
        return;
      }
      config = validation.data!;
    } else {
      // Validate form inputs
      const limitValidation = validateLimits(parallelExecutions, durationMinutes);
      if (!limitValidation.valid) {
        alert(limitValidation.error || "Invalid configuration");
        return;
      }
      
      config = {
        websocket_url: websocketUrl,
        parallel_executions: parallelExecutions,
        duration_minutes: durationMinutes,
      };
    }

    setIsLoading(true);
    try {
      const response = await api.post("/api/adversarial/parallel", config);

      const { group_id, session_ids, status, message } = response.data;
      console.log("Adversarial test started:", { group_id, session_ids, status, message });
      
      setGroupId(group_id);
      testDurationRef.current = config.duration_minutes;
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
    console.log("startPolling called with:", { sessionIdsToPoll, duration });
    
    setIsPolling(true);
    const pollingEndTime = duration * 60 * 1000; // Just the duration, not including 30 seconds
    const endTime = Date.now() + pollingEndTime;

    console.log(`Polling will run for ${pollingEndTime / 1000} seconds`);

    // Poll each session for messages
    sessionIdsToPoll.forEach((sessionId) => {
      // Initial fetch immediately
      fetchSessionMessages(sessionId);
      
      const interval = setInterval(() => {
        if (Date.now() < endTime) {
          fetchSessionMessages(sessionId);
        } else {
          console.log(`Polling ended for session ${sessionId}`);
          clearInterval(interval);
          delete sessionPollingIntervalsRef.current[sessionId];
        }
      }, 4000); // Poll every 4 seconds

      sessionPollingIntervalsRef.current[sessionId] = interval;
      console.log(`Started polling interval for session ${sessionId}`);
    });

    // Stop all polling after duration
    setTimeout(() => {
      console.log("Polling timeout reached, stopping all intervals");
      Object.values(sessionPollingIntervalsRef.current).forEach((interval) => {
        clearInterval(interval);
      });
      sessionPollingIntervalsRef.current = {};
      setIsPolling(false);
      
      // Show processing modal
      setShowProcessingModal(true);
      setProcessingStatus(0);
      
      // Animate through processing stages
      let currentStatus = 0;
      const statusInterval = setInterval(() => {
        currentStatus++;
        if (currentStatus < processingMessages.length) {
          setProcessingStatus(currentStatus);
        } else {
          clearInterval(statusInterval);
        }
      }, 6000); // Change status every 6 seconds (30 seconds total / 5 stages)
      
      // After 30 seconds, show completion modal
      setTimeout(() => {
        clearInterval(statusInterval);
        setShowProcessingModal(false);
        setShowCompletionModal(true);
      }, 30000); // 30 seconds cooldown
    }, pollingEndTime);
  };

  const fetchSessionMessages = async (sessionId: string) => {
    // Abort any existing request for this session
    if (abortControllersRef.current[sessionId]) {
      console.log(`Aborting previous request for session: ${sessionId}`);
      abortControllersRef.current[sessionId].abort();
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllersRef.current[sessionId] = abortController;
    
    try {
      console.log(`Fetching messages for session: ${sessionId}`);
      const response = await api.get(`/api/session/${sessionId}/messages`, {
        signal: abortController.signal,
      });
      const data: SessionMessages = response.data;
      
      console.log(`Received messages for ${sessionId}:`, {
        messageCount: data.message_count,
        messagesLength: data.messages?.length || 0,
        firstMessage: data.messages?.[0]
      });
      
      // Handle empty messages array - still update state to show empty state
      const messages = data.messages || [];
      
      // Messages are in descending order (newest first), so reverse for display
      const reversedMessages = messages.length > 0 ? [...messages].reverse() : [];
      const previousCount = previousMessageCountsRef.current[sessionId] || 0;
      const hasNewMessages = reversedMessages.length > previousCount;
      
      setSessionMessages((prev) => {
        const updated = {
          ...prev,
          [sessionId]: reversedMessages,
        };
        console.log(`Updated messages for ${sessionId}, total messages: ${reversedMessages.length}`);
        return updated;
      });
      
      // Update previous count
      previousMessageCountsRef.current[sessionId] = reversedMessages.length;
      
      // Scroll if there are new messages
      if (hasNewMessages) {
        setTimeout(() => {
          const container = chatContainerRefs.current[sessionId];
          if (container) {
            container.scrollTo({
              top: container.scrollHeight,
              behavior: 'smooth'
            });
          }
        }, 150);
      }
    } catch (error: any) {
      // Don't log error if request was aborted
      const isAborted = 
        error.name === 'CanceledError' || 
        error.name === 'AbortError' || 
        error.code === 'ERR_CANCELED' ||
        error.message === 'canceled' ||
        abortController.signal.aborted;
      
      if (isAborted) {
        console.log(`Request aborted for session ${sessionId}`);
        return;
      }
      
      console.error(`Error fetching messages for session ${sessionId}:`, error);
      if (error.response) {
        console.error("Response error:", error.response.status, error.response.data);
      } else if (error.request) {
        console.error("Request error:", error.request);
      }
    } finally {
      // Only remove abort controller if it's still the current one
      if (abortControllersRef.current[sessionId] === abortController) {
        delete abortControllersRef.current[sessionId];
      }
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
      // Abort all pending requests
      Object.values(abortControllersRef.current).forEach((controller) => {
        controller.abort();
      });
      abortControllersRef.current = {};
      chatContainerRefs.current = {};
    };
  }, []);

  // Start polling when sessionIds are set
  useEffect(() => {
    if (sessionIds.length > 0 && !isPolling) {
      console.log("Starting polling for sessions:", sessionIds);
      startPolling(sessionIds, testDurationRef.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionIds]);

  // Auto-scroll chat containers when messages update (fallback)
  useEffect(() => {
    Object.keys(sessionMessages).forEach((sessionId) => {
      const container = chatContainerRefs.current[sessionId];
      if (container) {
        // Check if user is near bottom (within 100px) before auto-scrolling
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        
        if (isNearBottom) {
          // Small delay to ensure DOM is updated
          setTimeout(() => {
            container.scrollTo({
              top: container.scrollHeight,
              behavior: 'smooth'
            });
          }, 100);
        }
      }
    });
  }, [sessionMessages]);

  const aiProviders = sessionIds.length > 0
    ? sessionIds.map((sessionId, i) => ({
        id: sessionId,
        name: `Agent Session ${i + 1}`,
        color: "text-[#B91C1C]",
      }))
    : Array.from({ length: 4 }, (_, i) => ({
        id: `activity-${i + 1}`,
        name: `Agent Session ${i + 1}`,
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
      router.push(`/dashboard/reports/${groupIdWithoutPrefix}`);
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
      {/* Processing Modal */}
      <Dialog open={showProcessingModal} onOpenChange={() => {}}>
        <DialogContent 
          className="bg-[#252525] border-[#3A3A3A] text-white"
          showCloseButton={false}
        >
          <DialogHeader>
            <DialogTitle className="text-white text-center">Processing Test Results</DialogTitle>
            <DialogDescription className="text-gray-400 text-center">
              Please wait while we generate your comprehensive report
            </DialogDescription>
          </DialogHeader>
          <div className="py-8 flex flex-col items-center justify-center space-y-6">
            {/* Animated Spinner */}
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 border-4 border-[#3A3A3A] rounded-full"></div>
              <div className="absolute inset-0 border-4 border-[#B91C1C] rounded-full border-t-transparent animate-spin"></div>
            </div>
            
            {/* Animated Status Text */}
            <div className="min-h-[60px] flex items-center justify-center">
              <p 
                key={processingStatus}
                className="text-xl font-semibold text-white text-center animate-fade-in"
              >
                {processingMessages[processingStatus] || processingMessages[0]}
                <span className="inline-flex ml-2">
                  <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
                </span>
              </p>
            </div>
            
            {/* Progress Indicator */}
            <div className="w-full max-w-xs">
              <div className="h-2 bg-[#1E1E1E] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[#B91C1C] rounded-full transition-all duration-500 ease-out"
                  style={{ 
                    width: `${((processingStatus + 1) / processingMessages.length) * 100}%` 
                  }}
                ></div>
              </div>
              <p className="text-xs text-gray-400 text-center mt-2">
                Step {processingStatus + 1} of {processingMessages.length}
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
              asChild
              className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
            >
              <Link 
                href={`/dashboard/reports/${groupId?.startsWith("grp-") 
                  ? groupId.substring(4) 
                  : groupId}`}
              >
                Open Report
              </Link>
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
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-[#1E1E1E]">
              <TabsTrigger value="form" className="data-[state=active]:bg-[#252525]">
                Enter Values
              </TabsTrigger>
              <TabsTrigger value="json" className="data-[state=active]:bg-[#252525]">
                JSON Config
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="form" className="space-y-4 py-4">
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
                  max="5"
                  value={parallelExecutions}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 1;
                    if (value > 5) {
                      alert("Parallel executions cannot exceed 5. Please upgrade your plan to use more parallel executions.");
                      setParallelExecutions(5);
                    } else {
                      setParallelExecutions(value);
                    }
                  }}
                  className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                />
                <p className="text-xs text-gray-400">Maximum: 5 (upgrade required for more)</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration_minutes" className="text-white">
                  Duration (minutes)
                </Label>
                <Input
                  id="duration_minutes"
                  type="number"
                  min="0.1"
                  max="5"
                  step="0.1"
                  value={durationMinutes}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value) || 1;
                    if (value > 5) {
                      alert("Duration cannot exceed 5 minutes. Please upgrade your plan to run longer tests.");
                      setDurationMinutes(5);
                    } else {
                      setDurationMinutes(value);
                    }
                  }}
                  className="bg-[#1E1E1E] border-[#3A3A3A] text-white"
                />
                <p className="text-xs text-gray-400">Maximum: 5 minutes (upgrade required for longer tests)</p>
              </div>
            </TabsContent>
            
            <TabsContent value="json" className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="json_config" className="text-white">
                  JSON Configuration
                </Label>
                <Textarea
                  id="json_config"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  className="bg-[#1E1E1E] border-[#3A3A3A] text-white font-mono text-sm min-h-[200px]"
                  placeholder={`{\n  "websocket_url": "ws://localhost:8000",\n  "parallel_executions": 3,\n  "duration_minutes": 1\n}`}
                />
                <p className="text-xs text-gray-400">
                  Required keys: websocket_url, parallel_executions, duration_minutes
                </p>
              </div>
            </TabsContent>
          </Tabs>
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
                  <div 
                    ref={(el) => {
                      chatContainerRefs.current[ai.id] = el;
                    }}
                    className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
                  >
                    {messages.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                        Waiting for messages...
                      </div>
                    ) : (
                      messages.map((msg, idx) => (
                        <div
                          key={`${msg.timestamp}-${idx}`}
                          className={`flex animate-message-popup ${
                            msg.type === "human" ? "justify-end" : "justify-start"
                          }`}
                          style={{ animationDelay: `${idx * 0.05}s` }}
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
