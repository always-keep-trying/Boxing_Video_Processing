import os
import pandas as pd
from audio_processing import BoxingAudio
from video_processing import BoxingVideo
import support_functions as SF

src_dir = os.path.dirname(__file__)
input_dir = os.path.abspath(os.path.join(src_dir, '..', 'input'))
output_dir = os.path.abspath(os.path.join(src_dir, '..', 'output'))

#video_file = os.path.join(input_dir,'testing.mp4')
video_file = os.path.join(input_dir,'VID20260309183144.mp4')

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
# add beginning
clips.append(['Beginning.mp4',SF.fmt_time(0), df_spread['Start'][1] ])
bounds = [0, audio.data_lenth]
for i,val in df_spread.iterrows():
    round_str = f"Round_{i}.mp4"
    start_time = val['Start']
    end_time = val['End']
    start_time = SF.offset_fmt_time(start_time,-2, bounds)
    end_time = SF.offset_fmt_time(end_time,+4, bounds)
    clips.append([round_str,start_time,end_time])
# add end
clips.append(['End.mp4',df_spread.iloc[-1,:]['End'],  SF.fmt_time(audio.data_lenth)])

vid.cut_video_multiple(clips)
print("finished")

## TODO: add readme
## TODO: need a frontend app (drag and drop, show status bar, wheel)
# TODO: audio does it exist? if so load the existing mp3 file and do not create a new one
# TODO: for audio processing you can't too many rounds in a video, considering the shortest is 2 min and 30 seconds rest