import unittest
from unittest.mock import patch, MagicMock, ANY # ANY is useful for complex argument matching
import os
import tempfile
import shutil # For robust cleanup

# Ensure src modules can be imported
import sys
if __name__ == "__main__" or __package__ is None: # For running a single test file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.converter import Converter, ConversionError
import ffmpeg # To access ffmpeg.Error for mocking

class TestConverter(unittest.TestCase):
    def setUp(self):
        self.converter = Converter()
        
        # Create a temporary directory for outputs
        self.temp_out_dir_obj = tempfile.TemporaryDirectory()
        self.temp_out_dir = self.temp_out_dir_obj.name
        
        # Create a dummy input file
        # We use NamedTemporaryFile to get a path, but then manage its lifecycle manually
        # to allow ffmpeg (mocked or real if not careful) to access it after closing.
        self.input_file_handle = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.input_file_path = self.input_file_handle.name
        self.input_file_handle.write(b"dummy mp4 data") # Write some data
        self.input_file_handle.close() # Close it so other processes can access

    def tearDown(self):
        # Clean up the dummy input file
        if os.path.exists(self.input_file_path):
            os.remove(self.input_file_path)
        # Clean up the temporary output directory
        self.temp_out_dir_obj.cleanup()

    @patch('src.core.converter.ffmpeg.run') # Patching ffmpeg.run directly
    def test_successful_conversion_mp4_to_mp3(self, mock_ffmpeg_run):
        # Simulate ffmpeg.run success: it doesn't create the file, the caller expects it to be there.
        # For the test, we can simulate its creation if we need to check os.path.exists,
        # but the primary check is if ffmpeg.run was called correctly.
        # The Converter's convert_media returns output_file_path, so that's what we check.

        output_filename = "test_output.mp3"
        expected_output_path = os.path.join(self.temp_out_dir, output_filename)

        # Simulate ffmpeg.run creating the file (optional, but good for completeness)
        def create_dummy_output(*args, **kwargs):
            # args[0] is the stream spec, which contains the output path
            # args[0][-1] is usually the output path in how ffmpeg-python builds args
            # However, it's safer to use the expected_output_path directly for side_effect.
            with open(expected_output_path, 'w') as f:
                f.write("dummy mp3 data")
            return (b"stdout", b"stderr") # ffmpeg.run returns (stdout, stderr)
        
        mock_ffmpeg_run.side_effect = create_dummy_output

        returned_path = self.converter.convert_media(self.input_file_path, expected_output_path, "mp3")

        self.assertEqual(returned_path, expected_output_path)
        # Check if ffmpeg.run was called.
        # The arguments to ffmpeg.run are complex (a stream specifier).
        # We can check parts of the arguments if direct comparison is too fragile.
        # For now, just check it was called. A more detailed check would inspect call_args.
        mock_ffmpeg_run.assert_called_once() 
        
        # Example of more detailed check (can be fragile due to internal ffmpeg-python changes):
        args, kwargs = mock_ffmpeg_run.call_args
        ffmpeg_command_args = args[0] # This is the list of command parts for ffmpeg
        self.assertIn('-i', ffmpeg_command_args)
        self.assertIn(self.input_file_path, ffmpeg_command_args)
        self.assertIn('libmp3lame', ffmpeg_command_args) # Check for acodec
        self.assertIn(expected_output_path, ffmpeg_command_args)
        self.assertTrue(os.path.exists(expected_output_path))


    @patch('src.core.converter.ffmpeg.run')
    def test_conversion_failure_ffmpeg_error(self, mock_ffmpeg_run):
        # Configure mock_ffmpeg_run to raise ffmpeg.Error
        # The error message should be in stderr, decoded.
        mock_ffmpeg_run.side_effect = ffmpeg.Error("ffmpeg_command", stdout=b"", stderr=b"Simulated ffmpeg error output")
        
        output_filename = "test_output_fail.mp3"
        output_path = os.path.join(self.temp_out_dir, output_filename)

        with self.assertRaisesRegex(ConversionError, "ffmpeg error: Simulated ffmpeg error output"):
            self.converter.convert_media(self.input_file_path, output_path, "mp3")

    def test_input_file_not_found(self):
        non_existent_file = os.path.join(self.temp_out_dir, "non_existent_input.mp4")
        output_path = os.path.join(self.temp_out_dir, "output.mp3")

        with self.assertRaisesRegex(FileNotFoundError, f"Input file not found: {non_existent_file}"):
            self.converter.convert_media(non_existent_file, output_path, "mp3")

    @patch('src.core.converter.ffmpeg.run')
    def test_successful_conversion_avi(self, mock_ffmpeg_run):
        output_filename = "test_output.avi"
        expected_output_path = os.path.join(self.temp_out_dir, output_filename)
        
        mock_ffmpeg_run.return_value = (b"",b"") # Simulate success

        self.converter.convert_media(self.input_file_path, expected_output_path, "avi")
        
        args, _ = mock_ffmpeg_run.call_args
        ffmpeg_command_args = args[0]
        self.assertIn('mpeg4', ffmpeg_command_args) # vcodec for AVI as per Converter
        self.assertIn('mp3', ffmpeg_command_args)   # acodec for AVI
        self.assertIn(expected_output_path, ffmpeg_command_args)

    @patch('src.core.converter.ffmpeg.run')
    def test_successful_conversion_mov(self, mock_ffmpeg_run):
        output_filename = "test_output.mov"
        expected_output_path = os.path.join(self.temp_out_dir, output_filename)
        
        mock_ffmpeg_run.return_value = (b"",b"") # Simulate success

        self.converter.convert_media(self.input_file_path, expected_output_path, "mov")
        
        args, _ = mock_ffmpeg_run.call_args
        ffmpeg_command_args = args[0]
        self.assertIn('libx264', ffmpeg_command_args) # vcodec for MOV
        self.assertIn('aac', ffmpeg_command_args)    # acodec for MOV
        self.assertIn(expected_output_path, ffmpeg_command_args)
        
    @patch('src.core.converter.ffmpeg.run')
    def test_output_directory_creation(self, mock_ffmpeg_run):
        # Test that the output directory is created if it doesn't exist
        nested_output_dir = os.path.join(self.temp_out_dir, "nested_dir")
        output_filename = "test_output.mp3"
        expected_output_path = os.path.join(nested_output_dir, output_filename)

        # Ensure nested_output_dir does not exist initially
        if os.path.exists(nested_output_dir):
            shutil.rmtree(nested_output_dir)
            
        self.assertFalse(os.path.exists(nested_output_dir))

        mock_ffmpeg_run.return_value = (b"",b"") # Simulate success

        self.converter.convert_media(self.input_file_path, expected_output_path, "mp3")
        
        self.assertTrue(os.path.exists(nested_output_dir)) # Check directory was created
        mock_ffmpeg_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
```
