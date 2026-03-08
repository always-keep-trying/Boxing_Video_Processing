import os
import pandas as pd
from audio_processing import BoxingAudio
from video_processing import BoxingVideo
import support_functions as SF

src_dir = os.path.dirname(__file__)
input_dir = os.path.abspath(os.path.join(src_dir, '..', 'input'))
output_dir = os.path.abspath(os.path.join(src_dir, '..', 'output'))

#video_file = os.path.join(input_dir,'testing.mp4')
video_file = os.path.join(input_dir,'VID20260223183734.mp4')

## Video
vid = BoxingVideo(video_file)
project_out_dir = vid.project_dir
vid.save_audio()
mp3_file = vid.audio_file

## Audio
audio = BoxingAudio(mp3_file, project_out_dir)
audio.main()

excel_file_path = audio.excel_file_path
df = pd.read_excel(excel_file_path)
print(f"Processing {max(df['Round'])} rounds total")

df_spread = df.pivot(index='Round', columns='BellType', values='TimeStamp')
clips = []
bounds = [0, audio.data_lenth]
for i,val in df_spread.iterrows():
    round_str = f"Round_{i}.mp4"
    start_time = val['Start']
    end_time = val['End']
    start_time = SF.offset_fmt_time(start_time,-2, bounds)
    end_time = SF.offset_fmt_time(end_time,+4, bounds)
    clips.append([round_str,start_time,end_time])

vid.cut_video_multiple(clips)
print("finished")




