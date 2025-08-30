import { useRef, useState } from 'react';
import { Camera, Image, X, Upload, Loader2, CheckCircle } from 'lucide-react';
import { useJourneyStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface ImageUploadProps {
  className?: string;
}

export function ImageUpload({ className }: ImageUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [previewImages, setPreviewImages] = useState<string[]>([]);
  
  const { 
    uploadedImages,
    isUploading,
    uploadError,
    uploadImage,
    removeUploadedImage,
    clearUploadedImages,
  } = useJourneyStore();

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    
    Array.from(files).forEach(async (file) => {
      if (file.type.startsWith('image/')) {
        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
          if (e.target?.result) {
            setPreviewImages(prev => [...prev, e.target!.result as string]);
          }
        };
        reader.readAsDataURL(file);
        
        // Upload file
        await uploadImage(file);
      }
    });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    handleFileSelect(files);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  const requestCameraAccess = async () => {
    try {
      // For web, we can't directly access camera like in React Native,
      // but we can use the file input with capture attribute
      if (fileInputRef.current) {
        fileInputRef.current.setAttribute('capture', 'environment');
        fileInputRef.current.click();
      }
    } catch (error) {
      console.error('Camera access error:', error);
    }
  };

  const removePreview = (index: number) => {
    setPreviewImages(prev => prev.filter((_, i) => i !== index));
    removeUploadedImage(index);
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Upload Area */}
      <div
        className={cn(
          "relative border-2 border-dashed rounded-lg p-6 transition-all duration-200",
          dragActive 
            ? "border-primary bg-primary/10" 
            : "border-border hover:border-primary/50 bg-card/50 backdrop-blur-sm"
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleInputChange}
          className="hidden"
        />
        
        <div className="flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={requestCameraAccess}
              disabled={isUploading}
              className={cn(
                "flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg",
                "hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {isUploading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Camera className="h-5 w-5" />
              )}
              <span>Take Photo</span>
            </button>
            
            <button
              onClick={openFileDialog}
              disabled={isUploading}
              className={cn(
                "flex items-center gap-2 px-4 py-2 border border-border rounded-lg",
                "hover:bg-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              <Image className="h-5 w-5" />
              <span>Choose Files</span>
            </button>
          </div>
          
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Or drag and drop images here
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              PNG, JPG, WEBP up to 10MB each
            </p>
          </div>
        </div>
        
        {/* Upload Status */}
        {isUploading && (
          <div className="absolute inset-0 bg-card/80 backdrop-blur-sm rounded-lg flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Uploading images...</span>
            </div>
          </div>
        )}
      </div>
      
      {/* Error Message */}
      {uploadError && (
        <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-sm text-destructive">{uploadError}</p>
        </div>
      )}
      
      {/* Preview Grid */}
      {previewImages.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">Uploaded Images ({previewImages.length})</h3>
            <button
              onClick={() => {
                setPreviewImages([]);
                clearUploadedImages();
              }}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Clear all
            </button>
          </div>
          
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {previewImages.map((preview, index) => (
              <div
                key={index}
                className="relative aspect-square rounded-lg overflow-hidden bg-muted group"
              >
                <img
                  src={preview}
                  alt={`Uploaded ${index + 1}`}
                  className="w-full h-full object-cover"
                />
                
                {/* Success indicator */}
                <div className="absolute top-2 left-2">
                  <CheckCircle className="h-4 w-4 text-success bg-white rounded-full" />
                </div>
                
                {/* Remove button */}
                <button
                  onClick={() => removePreview(index)}
                  className={cn(
                    "absolute top-2 right-2 p-1 bg-destructive text-destructive-foreground rounded-full",
                    "opacity-0 group-hover:opacity-100 transition-opacity"
                  )}
                >
                  <X className="h-3 w-3" />
                </button>
                
                {/* Upload indicator overlay */}
                {index >= uploadedImages.length && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <Loader2 className="h-5 w-5 text-white animate-spin" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Upload Tips */}
      {previewImages.length === 0 && (
        <div className="mt-4 p-4 bg-accent/50 rounded-lg">
          <h4 className="text-sm font-medium mb-2">📸 Photo Tips</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• Capture interesting landmarks or views along your journey</li>
            <li>• Include unique local details that tell your story</li>
            <li>• Photos help create a richer narrative experience</li>
          </ul>
        </div>
      )}
    </div>
  );
}
