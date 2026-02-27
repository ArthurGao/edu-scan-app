"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  selectedFile: File | null;
  previewUrl: string | null;
}

export default function UploadZone({
  onFileSelected,
  selectedFile,
  previewUrl,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleCameraClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    cameraInputRef.current?.click();
  };

  const handleGalleryClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    fileInputRef.current?.click();
  };

  // Preview state (shared between mobile and desktop)
  if (previewUrl) {
    return (
      <div
        onClick={handleClick}
        className="relative cursor-pointer rounded-xl border-2 border-dashed transition-all duration-200 border-indigo-300 bg-indigo-50/50"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="p-6 flex flex-col items-center gap-4">
          <div className="relative w-full max-w-md mx-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Selected problem"
              className="rounded-lg shadow-md max-h-64 w-auto mx-auto object-contain"
            />
            <div className="absolute -top-2 -right-2 bg-indigo-500 text-white rounded-full p-1">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </div>
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">
              {selectedFile?.name}
            </p>
            {/* Desktop: simple replace text */}
            <p className="text-xs text-gray-500 mt-1 hidden md:block">
              Click or drag to replace
            </p>
            {/* Mobile: two buttons to replace */}
            <div className="flex gap-3 mt-2 md:hidden">
              <button
                onClick={handleCameraClick}
                className="text-xs text-indigo-600 font-medium"
              >
                Retake photo
              </button>
              <span className="text-xs text-gray-300">|</span>
              <button
                onClick={handleGalleryClick}
                className="text-xs text-indigo-600 font-medium"
              >
                Choose another
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Desktop: drag & drop zone */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`hidden md:block relative cursor-pointer rounded-xl border-2 border-dashed transition-all duration-200 ${
          isDragging
            ? "border-indigo-500 bg-indigo-50"
            : "border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-indigo-50/30"
        }`}
      >
        <div className="p-12 flex flex-col items-center gap-4">
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center ${
              isDragging ? "bg-indigo-100" : "bg-gray-100"
            }`}
          >
            <svg
              className={`w-8 h-8 ${isDragging ? "text-indigo-500" : "text-gray-400"}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
              />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-base font-medium text-gray-700">
              {isDragging
                ? "Drop your image here"
                : "Drag & drop your homework image"}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or click to browse files
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Supports PNG, JPG, JPEG, WEBP
            </p>
          </div>
        </div>
      </div>

      {/* Mobile: two action buttons */}
      <div className="md:hidden space-y-3">
        <button
          onClick={handleCameraClick}
          className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-indigo-500 text-white rounded-xl font-medium text-base hover:bg-indigo-600 active:bg-indigo-700 transition-colors"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
            />
          </svg>
          Take Photo
        </button>
        <button
          onClick={handleGalleryClick}
          className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white text-gray-700 rounded-xl font-medium text-base border-2 border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/30 active:bg-indigo-50 transition-colors"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
            />
          </svg>
          Choose from Gallery
        </button>
        <p className="text-xs text-gray-400 text-center">
          Supports PNG, JPG, JPEG, WEBP
        </p>
      </div>
    </>
  );
}
