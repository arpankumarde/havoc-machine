"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Zap, LayoutDashboard, Home, Play, LogOut } from "lucide-react";
import { Streamdown } from "streamdown";
import Image from "next/image";
const RunPage = () => {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("userEmail");
    router.push("/login");
  };

  const aiProviders = Array.from({ length: 4 }, (_, i) => ({
    id: `activity-${i + 1}`,
    name: `Activity ${i + 1}`,
    color: "text-[#B91C1C]",
  }));

  const chatData = {
    "activity-1": [
      {
        role: "user",
        text: "Run chaos test on payment service",
      },
      {
        role: "assistant",
        text: `
  **Chaos Test Initiated**
  
  Latency injection has started on the **payment service** to simulate unstable network conditions.
        `,
      },
      {
        role: "user",
        text: "What components are being monitored during this test?",
      },
      {
        role: "assistant",
        text: `
  The following components are currently under observation:
  - Payment API response times
  - Downstream service error rates
  - Retry and fallback mechanisms
        `,
      },
      {
        role: "user",
        text: "Will this impact live users?",
      },
      {
        role: "assistant",
        text: `
  Traffic is being routed through controlled test scenarios only.  
  No impact on live users has been detected so far.
        `,
      },
    ],

    "activity-2": [
      {
        role: "user",
        text: "Check system resilience under load",
      },
      {
        role: "assistant",
        text: `
  ### Load Spike Simulation Started
  
  The system is now undergoing a simulated traffic surge to test performance limits.
        `,
      },
      {
        role: "user",
        text: "How high did the CPU usage go?",
      },
      {
        role: "assistant",
        text: `
  CPU utilization increased steadily and peaked at **85%**, indicating significant processing demand.
        `,
      },
      {
        role: "user",
        text: "Did any services fail during the test?",
      },
      {
        role: "assistant",
        text: `
  No service crashes or critical failures were observed.  
  All core services remained operational with acceptable response times.
        `,
      },
    ],

    "activity-3": [
      {
        role: "user",
        text: "Simulate network instability",
      },
      {
        role: "assistant",
        text: `
  ### Network Fault Injection In Progress
  
  Packet loss and intermittent connectivity are being introduced.
        `,
      },
      {
        role: "user",
        text: "What were the packet loss results?",
      },
      {
        role: "assistant",
        text: `
  **Results Recorded:**
  - Packet loss rate: **3%**
  - Retry success rate: **98%**
  - No data corruption detected
        `,
      },
    ],

    "activity-4": [
      {
        role: "user",
        text: "Test database failover mechanism",
      },
      {
        role: "assistant",
        text: `
  ### Database Failover Test Started
  
  Primary database instance was intentionally taken offline.
        `,
      },
      {
        role: "user",
        text: "How long did the failover take?",
      },
      {
        role: "assistant",
        text: `
  Failover completed in **4.2 seconds**, with traffic redirected to the replica automatically.
        `,
      },
      {
        role: "user",
        text: "Was manual intervention required?",
      },
      {
        role: "assistant",
        text: `
  No manual intervention was required.  
  All write operations resumed successfully, meeting high-availability requirements.
        `,
      },
    ],
  };

  return (
    <div className="min-h-screen bg-[#1E1E1E] text-white flex">
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
            {aiProviders.map((ai) => (
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
                  <span className="text-xs text-gray-400">Online</span>
                </div>

                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                  {(chatData[ai.id] || []).map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`
    max-w-[85%]
    px-4 py-3
    text-sm
    rounded-2xl
    ${
      msg.role === "user"
        ? "bg-[#B91C1C] text-white rounded-br-md"
        : "bg-[#1E1E1E] text-gray-300 border border-[#3A3A3A] rounded-bl-md"
    }
  `}
                      >
                        <div className="streamdown">
                          <Streamdown>{msg.text}</Streamdown>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default RunPage;
