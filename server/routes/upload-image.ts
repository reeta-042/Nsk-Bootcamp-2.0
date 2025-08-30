import { RequestHandler } from "express";
import multer from 'multer';
import path from 'path';

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({ 
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only JPEG, PNG, WEBP, and GIF are allowed.'));
    }
  }
});

export const uploadMiddleware = upload.single('image');

export const handleImageUpload: RequestHandler = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    // In a real application, you would:
    // 1. Save the file to cloud storage (AWS S3, Google Cloud Storage, etc.)
    // 2. Process/resize the image if needed
    // 3. Store metadata in a database
    // 4. Return the public URL

    // Mock response
    const mockImageUrl = `https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=400&fit=crop&t=${Date.now()}`;
    
    // Simulate upload delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    res.json({
      success: true,
      imageUrl: mockImageUrl,
      filename: req.file.originalname,
      size: req.file.size,
      uploadedAt: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error uploading image:', error);
    res.status(500).json({ error: 'Failed to upload image' });
  }
};
