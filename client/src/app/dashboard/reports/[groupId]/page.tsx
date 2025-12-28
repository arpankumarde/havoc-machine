"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Streamdown } from "streamdown";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

const ReportPage = () => {
  const params = useParams();
  const groupId = params.groupId as string;
  const [markdown, setMarkdown] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      if (!groupId) return;

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `https://sprintingn.s3.amazonaws.com/havoc-machine/${groupId}.md`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch report: ${response.statusText}`);
        }

        const text = await response.text();
        setMarkdown(text);
      } catch (err) {
        console.error("Error fetching report:", err);
        setError(
          err instanceof Error ? err.message : "Failed to load report"
        );
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [groupId]);

  return (
    <div className="min-h-screen bg-[#1E1E1E] text-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#252525] border-b border-[#3A3A3A] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <Link href="/dashboard/run">
            <Button
              variant="ghost"
              className="text-gray-300 hover:text-white hover:bg-[#B91C1C]/20"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-white">
              Adversarial Test Report
            </h1>
            <p className="text-sm text-gray-400">Group ID: {groupId}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="w-8 h-8 animate-spin text-[#B91C1C]" />
              <p className="text-gray-400">Loading report...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <p className="text-red-400 mb-4">{error}</p>
              <Button
                asChild
                className="bg-[#B91C1C] hover:bg-[#B91C1C]/80 text-white"
              >
                <Link href="/dashboard">
                  Go Back
                </Link>
              </Button>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg border border-gray-200 shadow-lg p-8">
            <div className="prose max-w-none text-gray-700 [&_h1]:text-gray-900 [&_h2]:text-gray-900 [&_h3]:text-gray-900 [&_h4]:text-gray-900 [&_h5]:text-gray-900 [&_h6]:text-gray-900 [&_strong]:text-gray-900 [&_code]:bg-gray-100 [&_code]:text-[#B91C1C] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_pre]:bg-gray-100 [&_pre]:border [&_pre]:border-gray-200 [&_pre]:text-gray-800 [&_a]:text-[#B91C1C] [&_a]:hover:text-[#B91C1C]/80 [&_table]:border-gray-300 [&_th]:border-gray-300 [&_td]:border-gray-300 [&_blockquote]:border-l-gray-300 [&_blockquote]:text-gray-600">
              <Streamdown>{markdown}</Streamdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;

